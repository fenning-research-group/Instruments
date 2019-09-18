import numpy as np
import matplotlib as plt
import os
import serial
import time
import h5py
import sys
import matplotlib.pyplot as plt
from frgpl.camera import camera
from frgpl.stage import stage
from frgpl.kepco import kepco
from frgpl.daq import daq
from frgpl.laser import laser
from frgpl.tec import omega
import datetime
import time
from mpl_toolkits.axes_grid1 import make_axes_locatable
from tqdm import tqdm

root = 'C:\\Users\\Operator\\Desktop\\frgPL'		#default folder to save data
if not os.path.exists(root):
	os.mkdir(root)
datafolder = os.path.join(root, 'Data')
if not os.path.exists(datafolder):
	os.mkdir(datafolder)
# calibrationfolder = os.path.join(root, 'Calibration')
# if not os.path.exists(calibrationfolder):
# 	os.mkdir(calibrationfolder)


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
		self.numIV = 20		#number of IV measurements to average
		self.numframes = 100	#number of image frames to average
		self.__temperature = 25	#TEC stage temperature setpoint (C) during measurement
		self.temperatureTolerance = 0.2	#how close to the setpoint we need to be to take a measurement (C)
		self.maxSoakTime = 60	# max soak time, in seconds, to wait for temperature to reach set point. If we reach this point, just go ahead with the measurement
		self.note = ''
		self._spotMap = None	# optical power map of laser spot, used for PL normalization
		self._sampleOneSun = None # fractional laser power with which to approximate one-sun injection levels
		self._sampleOneSunJsc = None # target Jsc, matching of which is used for one-sun injection level is approximated
		self._sampleOneSunSweep = None # fractional laser power vs photocurrent (Isc), fit to provide one-sun estimate
		self.__previewFigure = None	#handle for matplotlib figure, used for previewing most recent image results
		self.__previewAxes = [None, None]	# handle for matplotib axes, used to hold the image and colorbar
		self.__backgroundImage = None

		# data saving settings
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputDirectory = os.path.join(root, 'Data', todaysDate)	#default save locations is desktop/frgPL/Data/(todaysDate)
		self.sampleName = None
		self.__dataBuffer = [] # buffer to hold data files during sequential measurements of single sample. Held until a batch export

		# stage/positioning constants
		self.__sampleposition = (52361, 41000)	#position where TEC stage is centered in camera FOV, um
		self.__detectorposition = (67450, 102000)	#delta position between detector and sampleposition, um.
		self.__fov = (77000, 56000)	#dimensions of FOV, um

	@property
	def temperature(self):
		return self.__temperature

	@temperature.setter
	def temperature(self, t):
		if self.tec.setSetPoint(t):
			self.__temperature = t
		

	def connect(self):
		self.camera = camera()		# connect to FLIR camera
		self.kepco = kepco()		# connect to Kepco
		self.laser = laser()		# Connect to OSTECH Laser
		self.daq = daq()			# connect to NI-USB6000 DAQ
		self.stage = stage(sampleposition = self.__sampleposition)		# connect to FRG stage
		self.tec = omega()			# connect to omega PID controller, which is driving the TEC stage.
		
	def disconnect(self):
		try:
			self.camera.disconnect()
		except:
			print('Could not disconnect camera')

		try:
			self.kepco.disconnect()
		except:
			print('Could not disconnect Kepco')
		try:
			self.laser.disconnect()
		except:
			print('Could not disconnect OSTech Laser')
		try:
			self.daq.disconnect()
		except:
			print('Could not disconnect DAQ')
		try:
			self.stage.disconnect()
		except:
			print('Could not disconnect stage')
		try:
			self.tec.disconnect()
		except:
			print('Could not disconnect TEC controller')


	### basic use functions

	def setMeas(self, bias = None, laserpower = None, suns = None, saturationtime = None, temperature = None, numIV = None, numframes = None, note = ''):

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
						if laserpower > 1:
							print('Setting to max laser power ({0} suns)'.format(maxsuns))
							laserpower = 1
						else:
							print('Setting laser off')
							laserpower = 0
						# return False
		if saturationtime is None:
			saturationtime = self.saturationtime
		if temperature is None:
			temperature = self.temperature
		if numIV is None:
			numIV = self.numIV
		if numframes is None:
			numframes = self.numframes


		result = self.kepco.set(voltage = bias)
		if result:
			self.bias = bias
		else:
			print('Error setting kepco')
			# return False

		result = self.laser.set(power = laserpower)

		if result:
			self.laserpower = laserpower
		else:
			print('Error setting laser')
			# return False

		self.numIV = numIV
		self.numframes = numframes
		self.note = note

	def takeMeas(self, lastmeasurement = True, preview = True, imputeHotPixels = False):
		### takes a measurement with settings stored in method (can be set with .setMeas()).
		#	measurement settings + results are appended to .__dataBuffer
		#
		#	if .__dataBuffer is empty (ie, no measurements have been taken yet), takeMeas() will 
		#	automatically take a 0 bias, 0 laser power baseline measurement before the scheduled
		#	measurement.

		if len(self.__dataBuffer) == 0: # sample is being measured for the first time, take a baseline image
			print('New sample: taking a 0 bias, 0 illumination baseline image.')
			# store scheduled measurement parameters
			savedlaserpower = self.laserpower
			savedbias = self.bias
			savednote = self.note

			# take a 0 bias, 0 laserpower measurement, append to .__dataBuffer
			self.setMeas(bias = 0, laserpower = 0, note = 'automatic baseline image')
			self._waitForTemperature()
			measdatetime = datetime.datetime.now()
			temperature = self.tec.getTemperature()
			im, _, _ = self.camera.capture(frames = self.numframes, imputeHotPixels = imputeHotPixels)
			v, i = self.kepco.read(counts = self.numIV)
			irradiance = self._getOpticalPower()
			temperature = (temperature + self.tec.getTemperature()) / 2	#average the temperature from just before and after the measurement. Typically averaging >1 second of time here.
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
				'image_bgcorrected': im-im,
				'irradiance_ref': irradiance, 
				'temperature':	temperature,
				'temperature_setpoint': self.temperature
			}
			self.__dataBuffer.append(meas)	
			self.__backgroundImage = im  	#store background image for displaying preview

			# restore scheduled measurement parameters + continue 	
			self.setMeas(bias = savedbias, laserpower = savedlaserpower, note = savednote)

		if not self.__laserON and self.laserpower > 0:
			self.laser.on()
			self.__laserON = True
		if not self.__kepcoON and self.bias is not 0:
			self.kepco.on()	#turn on the kepco source
			self.__kepcoON = True

		time.sleep(self.saturationtime)

		#take image, take IV meas during image
		self._waitForTemperature()
		measdatetime = datetime.datetime.now()
		temperature = self.tec.getTemperature()
		im, _, _ = self.camera.capture(frames = self.numframes, imputeHotPixels = imputeHotPixels)
		v, i = self.kepco.read(counts = self.numIV)
		irradiance = self._getOpticalPower()
		temperature = (temperature + self.tec.getTemperature()) / 2	#average the temperature from just before and after the measurement. Typically averaging >1 second of time here.

		if self.__laserON and lastmeasurement:
			self.laser.off()
			self.__laserON = False
		if self.__kepcoON and lastmeasurement:
			self.kepco.off()
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
			'image_bgcorrected': im - self.__backgroundImage,
			'irradiance_ref': irradiance,
			'temperature': temperature,
			'temperature_setpoint': self.temperature
		}
		self.__dataBuffer.append(meas)

		if preview:
			self.displayPreview(im-self.__backgroundImage, v, i)

		return im, v, i

	def displayPreview(self, img, v, i):
		def handle_close(evt, self):
			self.__previewFigure = None
			self.__previewAxes = [None, None]
		
		if self.__previewFigure is None:	#preview window is not created yet, lets make it
			plt.ioff()
			self.__previewFigure, self.__previewAxes[0] = plt.subplots()
			divider = make_axes_locatable(self.__previewAxes[0])
			self.__previewAxes[1] = divider.append_axes('right', size='5%', pad=0.05)
			self.__previewFigure.canvas.mpl_connect('close_event', lambda x: handle_close(x, self))	# if preview figure is closed, lets clear the figure/axes handles so the next preview properly recreates the handles
			plt.ion()
			plt.show()

		for ax in self.__previewAxes:	#clear the axes
			ax.clear()
		img_handle = self.__previewAxes[0].imshow(img)
		self.__previewFigure.colorbar(img_handle, cax = self.__previewAxes[1])
		self.__previewAxes[0].set_title('{0} V, {1} A, {2} Laser'.format(v, i, self.laserpower))
		self.__previewFigure.canvas.draw()
		self.__previewFigure.canvas.flush_events()
		time.sleep(1e-4)		#pause allows plot to update during series of measurements 

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

		todaysDate = datetime.datetime.now().strftime('%Y%m%d')

		if self.sampleName is not None:
			fname = 'frgPL_{0}_{1:04d}_{2}.h5'.format(todaysDate, sampleNumber, self.sampleName)
		else:
			fname = 'frgPL_{0}_{1:04d}.h5'.format(todaysDate, sampleNumber)
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
			
			temp = info.create_dataset('notes', data = np.array([x.encode('utf-8') for x in data['note']]))
			temp.attrs['description'] = 'Any notes describing each measurement.'

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

			temp = settings.create_dataset('tempsp', data = np.array(data['temperature_setpoint']))
			temp.attrs['description'] = 'TEC stage temperature setpoint for each measurement.'


			if self.stage.position[0] is None:
				stagepos = self.__sampleposition
			else:
				stagepos = self.stage.position

			temp = settings.create_dataset('position', data = np.array(stagepos))
			temp.attrs['description'] = 'Stage position during measurement.'

			if self._sampleOneSun is not None:
				suns = [x/self._sampleOneSun for x in data['laserpower']]
				temp = settings.create_dataset('suns', data = np.array(suns))
				temp.attrs['description'] = 'PL injection level in terms of suns. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

			# calibrations
			calibrations = f.create_group('/calibrations')
			calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

			temp = calibrations.create_dataset('fov', data = np.array(data['cameraFOV']))
			temp.attrs['description'] = 'Camera field of view dimensions, in microns.'


			temp = settings.create_dataset('samplepos', data = np.array(self.__sampleposition))
			temp.attrs['description'] = 'Stage position (um)[x,y] where sample is centered in camera field of view'

			temp = settings.create_dataset('detectorpos', data = np.array(self.__detectorposition))
			temp.attrs['description'] = 'Stage position (um) [x,y] where photodetector is centered in camera field of view'

			temp = settings.create_dataset('camerafov', data = np.array(self.__fov))
			temp.attrs['description'] = 'Camera field of view (um) [x,y]'

			if self._spotMap is not None:
				temp = calibrations.create_dataset('spot', data = np.array(self._spotMap))
				temp.attrs['description'] = 'Map [y, x] of incident optical power across camera FOV, can be used to normalize PL images. Laser power set to 0.5 during spot mapping.'

				temp = calibrations.create_dataset('spotx', data = np.array(self._spotMapX))
				temp.attrs['description'] = 'X positions (um) for map of incident optical power across camera FOV, can be used to normalize PL images.'

				temp = calibrations.create_dataset('spoty', data = np.array(self._spotMap))
				temp.attrs['description'] = 'Y positions (um) for map of incident optical power across camera FOV, can be used to normalize PL images.'

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

			temp = rawdata.create_dataset('image_nobg', data = np.array(data['image_bgcorrected']), chunks = True, compression = 'gzip')
			temp.attrs['description'] = 'Background-subtracted images acquired for each measurement.'

			temp = rawdata.create_dataset('v', data = np.array(data['v_meas']))
			temp.attrs['description'] = 'Voltage measured during measurement'

			temp = rawdata.create_dataset('i', data = np.array(data['i_meas']))
			temp.attrs['description'] = 'Current (not current density!) measured during measurement'

			temp = rawdata.create_dataset('irr_ref', data = np.array(data['irradiance_ref']))
			temp.attrs['description'] = 'Measured irradiance @ photodetector during measurement. Note that the photodetector is offset from the sample FOV. Assuming that the laser spot is centered on the sample, this value is lower than the true sample irradiance. This value should be used in conjunction with a .spotMap() calibration map.'			

			temp = rawdata.create_dataset('temp', data = np.array(data['temperature']))
			temp.attrs['description'] = 'Measured TEC stage temperature during measurement. This value is the average of two temperature measurements, just before and after the image/kepco readings/photodetector readings are made. These two values typically span >1 second'

		print('Data saved to {0}'.format(fpath))
		if reset:
			self._sampleOneSun = None
			self._sampleOneSunSweep = None
			self._sampleOneSunJsc = None
			self.samplename = None
			self.__backgroundImage = None

			print('Note: sample name and one sun calibration results have been reset to None')
		
		self.__dataBuffer = []

	### calibration methods

	def findOneSun(self, jsc, area):
		### finds fraction laser power for which measured jsc = target value from solar simulator JV testing.
		# jsc: short circuit current density in mA/cm^2 (positive)
		# area: active area cm^2
		if jsc < 1:
			print('Please provide jsc in units of mA/cm^2, and area in units of cm^2')
			return False

		isc = -jsc * area / 1000 	#negative total current in amps, since kepco will be measuring total photocurrent as amps

		laserpowers = np.linspace(0,0.8, 7)[1:]	#skip 0, lean on lower end to reduce incident power
		self.kepco.set(voltage = 0)

		laserjsc = np.zeros(len(laserpowers))

		self.laser.set(power = laserpowers[0])		#set to first power before turning on laser
		self.laser.on()
		for idx, power in enumerate(laserpowers):
			self.laser.set(power = power)
			time.sleep(self.saturationtime)
			_,laserjsc[idx] = self.kepco.read(counts = 25)  
		self.laser.off()

		pfit = np.polyfit(laserjsc, laserpowers, 2)
		p = np.poly1d(pfit)	#polynomial fit object where x = measured jsc, y = laser power applied
		
		self._sampleOneSun = p(isc)
		self._sampleOneSunSweep = [laserpowers, laserjsc]
		self._sampleOneSunJsc = jsc

		return p(isc), laserpowers, laserjsc	#return laser power to match target jsc

	def calibrateSpot(self, numx = 21, numy = 21, rngx = None, rngy = None, laserpower = 0.5):
		### maps an area around the sample FOV, finds the optical power at each point
		if not self.stage._homed:
			self._stage.gohome()
		#default calibration area range = camera FOV
		if rngx is None:
			rngx = self.__fov[0]
		if rngy is None:
			rngy = self.__fov[1]

		xpos = np.linspace(self.__detectorposition[0] - (rngx/2), self.__detectorposition[0] + (rngx/2), numx).astype(int)
		ypos = np.linspace(self.__detectorposition[1] - (rngy/2), self.__detectorposition[1] + (rngy/2), numy).astype(int)
		

		self.laser.set(power = laserpower)
		self._spotMap = np.zeros((numx, numy))
		self._spotMapX = xpos
		self._spotMapY = ypos
		
		print('Moving to start position ({0}, {1})'.format(xpos[0], ypos[0]))
		if not self.stage.moveto(x = xpos[0], y = ypos[0]):
			print('Error moving stage to starting position ({0}, {1}) - stage is probably not homed. run method ._stage.gohome()'.format(xpos[0], ypos[0]))		
			return False

		self.laser.on()
		flip = 1
		for m, x in enumerate(xpos):
			flip = flip * -1
			self.stage.moveto(x = x)
			for n in range(len(ypos)):
				if flip > 0:		#use nn instead of n, accounts for snaking between lines
					nn = len(ypos) - n - 1
				else:
					nn = n
				self.stage.moveto(y = ypos[nn])
				self._spotMap[nn,m] = self._getOpticalPower()
		self.laser.off()

		self.stage.moveto(x = self.__sampleposition[0], y = self.__sampleposition[1])	#return stage to camera FOV

	### group measurement methods

	def takeRseMeas(self, vmpp, voc, vstep = 0.005):
		# generate list of biases spanning from vmpp to at least voc, with intervals of vstep
		biases = [vmpp]
		while biases[-1] < voc:
			biases.append(biases[-1] + vstep)

		with tqdm(total = len(biases), desc = 'Rse EL', leave = False) as pb:
			for bias in biases[0:-1]:	#measure all but last with lastmeasurement = True (doesnt turn kepco off between measurements). Last measurement is normal
				self.setMeas(bias = bias, laserpower = 0, note = 'part of Rse measurement series')
				self.takeMeas(lastmeasurement = False)
				pb.update(1)

			self.setMeas(bias = biases[-1], laserpower = 0, note = 'part of Rse measurement series')
			self.takeMeas(lastmeasurement = True)		
			pb.update(1)

	def takePLIVMeas(self, vmpp, voc, jsc, area):
		### Takes images at varied bias and illumination for PLIV fitting of cell parameters
		### based on https://doi.org/10.1016/j.solmat.2012.10.010

		if self._sampleOneSun is None:
			self.findOneSun(jsc = jsc, area = area)		# calibrate laser power to one-sun injection by matching jsc from solar simulator measurement

		# full factorial imaging across voltage (vmpp - voc) and illumination (0.2 - 1.0 suns). 25 images
		allbiases = np.linspace(vmpp, voc, 5)		#range of voltages used for image generation
		allsuns = np.linspace(0.2, 1, 5)			#range of suns (pl injection) used for image generation

		self.setMeas(bias = 0, suns = 1, temperature = 23, note = 'PLIV - open circuit PL image')
		self.takeMeas()

		with tqdm(total = allbiases.shape[0] * allsuns.shape[0], desc = 'PLIV', leave = False) as pb:
			for suns in allsuns:
				for bias in allbiases:
					self.setMeas(bias = bias, suns = suns, temperature = 25, note = 'PLIV')
					self.takeMeas(lastmeasurement = False)
					pb.update(1)


		self.laser.off()	#turn off the laser and kepco
		self.kepco.off()

	def takePVRD2Meas(self, samplename, note, vmpp, voc, jsc, area = 25.08, vstep = 0.005):
		self.takeRseMeas(
			vmpp = vmpp,
			voc = voc,
			vstep = vstep
			)

		self.takePLIVMeas(
			vmpp = vmpp,
			voc = voc,
			jsc = jsc,
			area = area
			)

		self.setMeas(bias = -12, laserpower = 0, note = 'Reverse Bias EL')
		self.takeMeas()

		storedOutputDir = self.outputDirectory
		self.outputDirectory = os.path.join(root, 'PVRD2 Degradation Study')
		if not os.path.exists(self.outputDirectory):
			os.mkdir(self.outputDirectory)
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputDirectory = os.path.join(root, 'PVRD2 Degradation Study', todaysDate)
		if not os.path.exists(self.outputDirectory):
			os.mkdir(self.outputDirectory)

		self.save(samplename = samplename, note = note, reset = True)

		self.outputDirectory = storedOutputDir		

	### helper methods
	def _waitForTemperature(self):
		refreshDelay = 0.5	#how long to wait between temperautre checks, in seconds
		reachedTemp = False

		startTime = time.time()
		while (not reachedTemp) and (time.time() - startTime <= self.maxSoakTime):
			currentTemp = self.tec.getTemperature()
			if np.abs(currentTemp - self.temperature) <= self.temperatureTolerance:
				reachedTemp = True
			else:
				time.sleep(refreshDelay)

		if not reachedTemp:
			print('Did not reach {0} C within {1} seconds: starting measurement anyways.'.format(self.temperature, self.maxSoakTime))

		return True

	def _getOpticalPower(self):
		### reads signal from photodetector, converts to optical power using calibration vs thorlabs Si power meter (last checked 2019-08-20)
		calibrationFit = [-0.1145, 9.1180]; #polyfit of detector reading vs (Si power meter / detector reading), 2019-08-20
		voltage, _, _ = self.daq.acquire()
		power = voltage * (calibrationFit[0]*voltage + calibrationFit[1])	#measured optical power, units of mW/cm^2

		return power


	#def normalizePL(self):
	### used laser spot power map to normalize PL counts to incident optical power
