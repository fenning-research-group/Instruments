import numpy as np
import matplotlib as plt
import os
import serial
import time
import h5py
import sys
from camera import camera
from stage import stage
from kepco import kepco
from daq import daq
from laser import laser
import datetime

root = 'C:\\Users\\Operator\\Desktop\\frgPL'
if not os.path.exists(root):
	os.mkdir(root)
datafolder = os.path.join(root, 'Data')
if not os.path.exists(datafolder):
	os.mkdir(datafolder)

class control:

	def __init__(self, kepcoport = 'COM5',laserport = 'COM1'):
		# hardware properties
		self.kepcoport = kepcoport
		self.laserport = laserport
		self.__laserON = False
		self.__kepcoON = False
		self.__cameraON = False

		# measurement settings
		self.bias = 0			#bias applied to sample
		self.laserpower = 0	#current supplied to laser ###may replace this with n_suns, if calibration is enabled
		self.saturationtime = 0.5	#delay between applying voltage/illumination and beginning measurement
		self.numIV = 10		#number of IV measurements to average
		self.numframes = 50	#number of image frames to average
		self.note = ''
		self._spotMap = None	# optical power map of laser spot, used for PL normalization
		self._sampleOneSun = None # fractional laser power with which to approximate one-sun injection levels
		self._sampleOneSunJsc = None # target Jsc, matching of which is used for one-sun injection level is approximated
		self._sampleOneSunSweep = None # fractional laser power vs photocurrent (Isc), fit to provide one-sun estimate
		
		# data saving settings
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputDirectory = os.path.join(root, 'Data', todaysDate)	#default save locations is desktop/frgPL/Data/(todaysDate)
		self.sampleName = None
		self.__dataBuffer = [] # buffer to hold data files during sequential measurements of single sample. Held until a batch export

		# stage/positioning constants
		self.__sampleposition = (34915, 69000)	#position where TEC stage is centered in camera FOV, um
		self.__detectorposition = (49333, 125500)	#delta position between detector and sampleposition, um.
		self.__fov = (38000, 34000)	#dimensions of FOV, um

	def connect(self):
		self._camera = camera()		# connect to FLIR camera
		self._kepco = kepco()		# connect to Kepco
		self._laser = laser()		# Connect to OSTECH Laser
		self._daq = daq()			# connect to NI-USB6000 DAQ
		self._stage = stage()		# connect to FRG stage
		
	def disconnect(self):
		try:
			self._camera.disconnect()
		except:
			print('Could not disconnect camera')

		try:
			self._kepco.disconnect()
		except:
			print('Could not disconnect Kepco')
		try:
			self._laser.disconnect()
		except:
			print('Could not disconnect OSTech Laser')
		try:
			self._daq.disconnect()
		except:
			print('Could not disconnect DAQ')
		try:
			self._stage.disconnect()
		except:
			print('Could not disconnect stage')


	### basic use functions

	def setMeas(self, bias = None, laserpower = None, suns = None, saturationtime = None, numIV = None, numframes = None, note = ''):

		if bias is None:
			bias = self.bias
		if laserpower is None:
			if suns is None:
				laserpower = self.laserpower
			else:
				if self._sampleOneSun is None:
					print('Error: can\'t use "suns =" without calibration -  please run .findOneSun to calibrate one-sun power level for this sample.')
					return False
				else:
					laserpower = suns * self._sampleOneSun
					if (laserpower > 1) or (laserpower < 0):
						maxsuns = 1/self._sampleOneSun
						print('Error: {0} suns is out of range! Based on laser power and current sample, allowed suns range = 0 - {1}.'.format(suns, maxsuns))
						return False
		if saturationtime is None:
			saturationtime = self.saturationtime
		if numIV is None:
			numIV = self.numIV
		if numframes is None:
			numframes = self.numframes

		result = self._kepco.set(voltage = bias)
		if result:
			self.bias = bias
		else:
			print('Error setting kepco')
			# return False

		result = self._laser.set(power = laserpower)

		if result:
			self.laserpower = laserpower
		else:
			print('Error setting laser')
			# return False

		self.numIV = numIV
		self.numframes = numframes
		self.note = note

	def takeMeas(self, lastmeasurement = True):
		### takes a measurement with settings stored in method (can be set with .setMeas()).
		#	measurement settings + results are appended to .__dataBuffer
		#
		#	if .__dataBuffer is empty (ie, no measurements have been taken yet), takeMeas() will 
		#	automatically take a 0 bias, 0 laser power baseline measurement before the scheduled
		#	measurement.

		if len(self.__dataBuffer) == 0: # sample is being measured for the first time, take a baseline image
			# store scheduled measurement parameters
			savedlaserpower = self.laserpower
			savedbias = self.bias
			savednote = self.note

			# take a 0 bias, 0 laserpower measurement, append to .__dataBuffer
			self.setMeas(bias = 0, laserpower = 0, note = 'automatic baseline image')
			measdatetime = datetime.datetime.now()
			im, _, _ = self._camera.capture(frames = self.numframes, imputeHotPixels = True)
			v, i = self._kepco.read(counts = self.numIV)
			meas = {
				'sample': 	self.sampleName,
				'note':		self.note,
				'date': 	measdatetime.strftime('%Y-%m-%d'),
				'time':		measdatetime.strftime('%H:%M:%S'),
				'cameraFOV':self.__fov,
				'bias':		self.bias,
				'laserpower': self.laserpower,
				'saturationtime': self.saturationtime,
				'numIV':	self.numIV,
				'numframes':self.numframes,
				'v_meas':	v,
				'i_meas':	i,
				'image':	im,
			}
			self.__dataBuffer.append(meas)	

			# restore scheduled measurement parameters + continue 	
			self.laserpower = savedlaserpower
			self.bias = savedbias
			self.note = savednote

		if not self.__laserON and self.laserpower > 0:
			self._laser.on()
			self.__laserON = True
		if not self.__kepcoON and self.bias is not 0:
			self._kepco.on()	#turn on the kepco source
			self.__kepcoON = True

		time.sleep(self.saturationtime)

		#take image, take IV meas during image
		measdatetime = datetime.datetime.now()
		im, _, _ = self._camera.capture(frames = self.numframes, imputeHotPixels = True)
		v, i = self._kepco.read(counts = self.numIV)

		if self.__laserON and lastmeasurement:
			self._laser.off()
			self.__laserON = False
		if self.__kepcoON and lastmeasurement:
			self._kepco.off()
			self.__kepcoON = False

		meas = {
			'sample': 	self.sampleName,
			'note':		self.note,
			'date': 	measdatetime.strftime('%Y-%m-%d'),
			'time':		measdatetime.strftime('%H:%M:%S'),
			'cameraFOV':self.__fov,
			'bias':		self.bias,
			'laserpower': self.laserpower,
			'saturationtime': self.saturationtime,
			'numIV':	self.numIV,
			'numframes':self.numframes,
			'v_meas':	v,
			'i_meas':	i,
			'image':	im,
		}
		self.__dataBuffer.append(meas)

		return im, v, i

	def save(self, samplename = None, note = None, outputdirectory = None, reset = True):
		if len(self.__dataBuffer) == 0:
			print('Data buffer is empty - no data to save!')
			return False

		## figure out the sample directory, name, total filepath
		if samplename is not None:
			self.sampleName = samplename

		if outputdirectory is not None:
			self.outputDirectory = outputdirectory
		if not os.path.exists(self.outputDirectory):
			os.mkdir(self.outputDirectory)

		fids = os.listdir(self.outputDirectory)
		sampleNumber = 1
		for fid in fids:
			if 'frgPL' in fid:
				sampleNumber = sampleNumber + 1

		if self.sampleName is not None:
			fname = 'frgPL_{0:04d}_{1}.h5'.format(sampleNumber, self.sampleName)
		else:
			fname = 'frgPL_{0:04d}.h5'.format(sampleNumber)
			self.sampleName = ''

		fpath = os.path.join(self.outputDirectory, fname)

		## build each category in h5 file

		### example dataset saved to _dataBuffer by .takeMeas
		# meas = {
		# 	'sample': 	self.sampleName,
		# 	'date': 	measdatetime.strftime('%Y-%m-%d'),
		# 	'time':		measdatetime.strftime('%H:%M:%S'),
		# 	'cameraFOV':self.__fov,
		# 	'bias':		self.bias,
		# 	'laserpower': self.laserpower,
		# 	'saturationtime': self.saturationtime,
		# 	'numIV':	self.numIV,
		# 	'numframes':self.numframes,
		# 	'v_meas':	v,
		# 	'i_meas':	i,
		# 	'image':	im,
		# }

		numData = len(self.__dataBuffer)

		data = {}
		for field in self.__dataBuffer[0].keys():
			data[field] = []
		### field to store normalized PL images
		# if self._spotmap is not None:
		# 	data['image_norm'] = []

		for meas in self.__dataBuffer:
			for field, measdata in meas.items():
				data[field].append(measdata)
				### normalize PL images here
				# if field is 'image' and self._spotmap is not None:
				# 	data['image_norm']


		## write h5 file

		with h5py.File(fpath, 'w') as f:
			# sample info
			info = f.create_group('/info')
			info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
			temp = info.create_dataset('name', data = self.sampleName.encode('utf-8'))
			temp.attrs['description'] = 'Sample name.'

			date = info.create_dataset('date', data = np.array([x.encode('utf-8') for x in data['date']]))
			temp.attrs['description'] = 'Measurement date.'

			
			temp = info.create_dataset('time', data =  np.array([x.encode('utf-8') for x in data['time']]))
			temp.attrs['description'] = 'Measurement time of day.'


			# measurement settings
			settings = f.create_group('/settings')
			settings.attrs['description'] = 'Settings used for measurements.'

			temp = settings.create_dataset('vbias', data = np.array(data['bias']))
			temp.attrs['description'] = 'Nominal voltage bias set by Kepco during measurement.'

			temp = settings.create_dataset('laserpower', data = np.array(data['laserpower']))
			temp.attrs['description'] = 'Fractional laser power during measurement. Calculated as normalized laser current (max current = 55 A). Laser is operated at steady state.'

			temp = settings.create_dataset('sattime', data = np.array(data['saturationtime']))
			temp.attrs['description'] = 'Saturation time for laser/bias conditioning prior to sample measurement. Delay between applying condition and measuring, in seconds.'

			temp = settings.create_dataset('numIV', data = np.array(data['numIV']))
			temp.attrs['description'] = 'Number of current/voltage measurements averaged by Kepco when reading IV.'

			temp = settings.create_dataset('numframes', data = np.array(data['numframes']))
			temp.attrs['description'] = 'Number of camera frames averaged when taking image.'

			if self._sampleOneSun is not None:
				suns = [x/self._sampleOneSun for x in data['laserpower']]
				temp = settings.create_dataset('suns', data = np.array(suns))
				temp.attrs['description'] = 'PL injection level in terms of suns. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

			# calibrations
			calibrations = f.create_group('/calibrations')
			calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

			temp = calibrations.create_dataset('fov', data = np.array(data['cameraFOV']))
			temp.attrs['description'] = 'Camera field of view dimensions, in microns.'

			if self._spotMap is not None:
				temp = calibrations.create_dataset('spot', data = np.array(self._spotMap))
				temp.attrs['description'] = 'Map of incident optical power across camera FOV, can be used to normalize PL images.'

			if self._sampleOneSunSweep is not None:
				temp = calibrations.create_dataset('onesunsweep', data = np.array(self._sampleOneSunSweep))
				temp.attrs['description'] = 'Laser current vs photocurrent, measured for this sample. Column 1: fractional laser current. Column 2: total photocurrent (Isc), NOT current density (Jsc). Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

				temp = calibrations.create_dataset('onesun', data = np.array(self._sampleOneSun))
				temp.attrs['description'] = 'Fractional laser current used to approximate a one-sun injection level. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

				temp = calibrations.create_dataset('onesunjsc', data = np.array(self._sampleOneSunJsc))
				temp.attrs['description'] = 'Target Jsc (NOT Isc) used to approximate a one-sun injection level. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

			# raw data
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Raw measurements taken during imaging'

			temp = rawdata.create_dataset('image', data = np.array(data['image']), chunks = True, compression = 'gzip')
			temp.attrs['description'] = 'Raw images acquired for each measurement.'

			temp = rawdata.create_dataset('v', data = np.array(data['v_meas']))
			temp.attrs['description'] = 'Voltage measured during measurement'

			temp = rawdata.create_dataset('i', data = np.array(data['i_meas']))
			temp.attrs['description'] = 'Current (not current density!) measured during measurement'

		print('Data saved to {0}'.format(fpath))
		if reset:
			self._sampleOneSun = None
			self._sampleOneSunSweep = None
			self._sampleOneSunJsc = None
			self.samplename = None

			print('Note: sample name and one sun calibration results have been reset to None')
			
	### calibration methods

	def findOneSun(self, jsc, area):
		### finds fraction laser power for which measured jsc = target value from solar simulator JV testing.
		# jsc: short circuit current density in mA/cm^2 (positive)
		# area: active area cm^2
		if jsc < 1:
			print('Please provide jsc in units of mA/cm^2, and area in units of cm^2')
			return False

		isc = -jsc * area 	#negative total current, since kepco will be measuring total photocurrent

		laserpowers = np.linspace(0,0.8, 7)[1:]	#skip 0, lean on lower end to reduce incident power
		self._kepco.set(voltage = 0)

		laserjsc = np.zeros(len(laserpowers))

		self._laser.set(power = laserpowers[0])		#set to first power before turning on laser
		self._laser.on()
		for idx, power in enumerate(laserpowers):
			self._laser.set(power = power)
			time.sleep(self._saturationtime)
			_,laserjsc[idx] = self._kepco.read(counts = 25)  
		self._laser.off()

		pfit = np.polyfit(laserjsc, laserpowers, 2)
		p = np.poly1d(pfit)	#polynomial fit object where x = measured jsc, y = laser power applied
		
		self._sampleOneSun = p(isc)
		self._sampleOneSunSweep = [laserpowers, laser]
		self._sampleOneSunJsc = jsc

		return p(isc), laserpowers, laserjsc	#return laser power to match target jsc

	def calibrateSpot(self, numx = 21, numy = 21, rngx = None, rngy = None, laserpower = 0.5):
		### maps an area around the sample FOV, finds the optical power at each point

		#default calibration area range = camera FOV
		if rngx is None:
			rngx = self.__fov[0]
		if rngy is None:
			rngy = self.__fov[1]

		xpos = np.linspace(self.__detectorposition[0] - (rngx/2), self.__detectorposition[0] + (rngx/2), numx).astype(int)
		ypos = np.linspace(self.__detectorposition[1] - (rngy/2), self.__detectorposition[1] + (rngy/2), numy).astype(int)
		

		self._laser.set(power = laserpower)
		self._spotMap = np.zeros((numx, numy))
		
		print('Moving to start position ({0}, {1})'.format(xpos[0], ypos[0]))
		if not self._stage.moveto(x = xpos[0], y = ypos[0]):
			print('Error moving stage to starting position ({0}, {1}) - stage is probably not homed. run method ._stage.gohome()'.format(xpos[0], ypos[0]))		
			return False

		self._laser.on()
		flip = 1
		for m, x in enumerate(xpos):
			flip = flip * -1
			self._stage.moveto(x = x)
			for n in range(len(ypos)):
				if flip > 0:		#use nn instead of n, accounts for snaking between lines
					nn = len(ypos) - n - 1
				else:
					nn = n
				self._stage.moveto(y = ypos[nn])
				self._spotMap[nn,m] = self.getOpticalPower()
		self._laser.off()

		self._stage.moveto(x = self.__sampleposition[0], y = self.__sampleposition[1])	#return stage to camera FOV

	### helper methods

	def getOpticalPower(self):
		### reads signal from photodetector, converts to optical power using calibration vs thorlabs Si power meter (last checked 2019-08-20)
		calibrationFit = [-0.1145, 9.1180]; #polyfit of detector reading vs (Si power meter / detector reading), 2019-08-20
		voltage, _, _ = self._daq.acquire()
		power = voltage * (calibrationFit[0]*voltage + calibrationFit[1])	#measured optical power, units of mW/cm^2

		return power

	#def progressbar(self, it, prefix="", size=60, file=sys.stdout):
		# count = len(it)
		# def show(j):
		# 	x = int(size*j/count)
		# 	file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
		# 	file.flush()        
		# show(0)
		# for i, item in enumerate(it):
		# 	yield item
		# 	show(i+1)
		# file.write("\n")
		# file.flush()
	#def normalizePL(self):
	### used laser spot power map to normalize PL counts to incident optical power
