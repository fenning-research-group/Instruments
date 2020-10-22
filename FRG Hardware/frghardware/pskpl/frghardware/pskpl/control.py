import numpy as np
import matplotlib as plt
import os
import serial
import time
import h5py
import sys
import matplotlib.pyplot as plt
from frghardware.components.stage import PLStage
from frghardware.components.camera import Hayear
# from frghardware.components.kepco import Kepco
# from frghardware.components.daq import PLDAQ
# from frghardware.components.laser import Laser808
from frghardware.components.tec import Omega
import datetime
import time
from tqdm import tqdm
import cv2

root = 'C:\\Users\\Operator\\Desktop\\frgPL'		#default folder to save data
if not os.path.exists(root):
	os.mkdir(root)
datafolder = os.path.join(root, 'Data')
if not os.path.exists(datafolder):
	os.mkdir(datafolder)
calibrationfolder = os.path.join(root, 'Calibration')
if not os.path.exists(calibrationfolder):
	os.mkdir(calibrationfolder)


class Control2:

	def __init__(self,spotmapnumber = None):
		# hardware properties
		self.camid_550 = 0
		self.camid_720 = 1
		self.__temperature = 25	#TEC stage temperature setpoint (C) during measurement
		
		# data saving settings
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputDirectory = os.path.join(root, 'Data', todaysDate)	#default save locations is desktop/frgPL/Data/(todaysDate)
		self.sampleName = None
		self.__dataBuffer = [] # buffer to hold data files during sequential measurements of single sample. Held until a batch export

		# stage/positioning constants
		self.__sampleposition = (39, 90)	#position where TEC stage is centered in camera FOV, mm
		self.__detectorposition = (64, 117)	#absolute position of detector centered in FOV, mm.
		self.__fov = (77, 56)	#dimensions of FOV, mm

		self.connect()
		# self.loadSpotCalibration(spotmapnumber)
	@property
	def temperature(self):
		return self.__temperature

	@temperature.setter
	def temperature(self, t):
		self.tec.setpoint = t
		self.__temperature = t

		

	def connect(self):
		self.cam550 = Hayear(self.camid_550)
		self.cam550.exposure = -5
		self.cam720 = Hayear(self.camid_720)
		self.cam720.exposure = -5
		# self.camera = FLIR()		# connect to FLIR camera
		# self.kepco = Kepco()		# connect to Kepco
		# self.kepco.set(voltage=0)   # set voltage to 0, seems to solve current compliance issues
		# self.laser = Laser808()		# Connect to OSTECH Laser
		# self.daq = PLDAQ()			# connect to NI-USB6000 DAQ
		self.stage = PLStage(sampleposition = self.__sampleposition)		# connect to FRG stage
		# self.tec = Omega('COM15')			# connect to omega PID controller, which is driving the TEC stage.
		
	def disconnect(self):
		try:
			self.cam550.disconnect()
			self.cam720.disconnect()
		except:
			print('Could not disconnect camera')

		# try:
		# 	self.kepco.disconnect()
		# except:
		# 	print('Could not disconnect Kepco')
	
		# try:
		# 	self.daq.disconnect()
		# except:
		# 	print('Could not disconnect DAQ')
		try:
			self.stage.disconnect()
		except:
			print('Could not disconnect stage')
		try:
			self.tec.disconnect()
		except:
			print('Could not disconnect TEC controller')


	### basic use functions
	def capture(self, samplename, frames = 10, note = '', save_img = False):
		im550 = self.cam550.capture(frames)
		im720 = self.cam550.capture(frames)

		self.save(
			samplename,
			im550,
			im720, 
			note = note,
			save_img = save_img
			)


	def save(self, samplename, img1, img2, x = None, y = None, note = '', outputdirectory = None, reset = True, save_img = False):

		## figure out the sample directory, name, total filepath
		if samplename is not None:
			self.sampleName = samplename

		if outputdirectory is not None:
			self.outputDirectory = outputdirectory
		if not os.path.exists(self.outputDirectory):
			os.mkdir(self.outputDirectory)

		if x is None:
			x = self.stage.position[0]
		if y is None:
			y = self.stage.position[1]

		fids = os.listdir(self.outputDirectory)
		sampleNumber = 1
		for fid in fids:
			if 'frg_pskPL' in fid:
				sampleNumber = sampleNumber + 1

		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		currentTime = datetime.datetime.now().strftime('%H:%M:%S')
		if self.sampleName is not None:
			fname = 'frg_pskPL_{0}_{1:04d}_{2}.h5'.format(todaysDate, sampleNumber, self.sampleName)
		else:
			fname = 'frg_pskPL_{0}_{1:04d}.h5'.format(todaysDate, sampleNumber)
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

		## write h5 file

		with h5py.File(fpath, 'w') as f:
			# sample info
			info = f.create_group('/info')
			info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
			temp = info.create_dataset('name', data = self.sampleName.encode('utf-8'))
			temp.attrs['description'] = 'Sample name.'
			
			temp = info.create_dataset('notes', data = note.encode('utf-8'))
			temp.attrs['description'] = 'Any notes describing each measurement.'

			date = info.create_dataset('date', data = todaysDate.encode('utf-8'))
			temp.attrs['description'] = 'Measurement date.'
			
			temp = info.create_dataset('time', data =  currentTime.encode('utf-8'))
			temp.attrs['description'] = 'Measurement time of day.'


			# # measurement settings
			settings = f.create_group('/settings')
			settings.attrs['description'] = 'Settings used for measurements.'

			# temp = settings.create_dataset('vbias', data = np.array(data['bias']))
			# temp.attrs['description'] = 'Nominal voltage bias set by Kepco during measurement.'

			# temp = settings.create_dataset('notes', data = np.array([x.encode('utf-8') for x in data['note']]))
			# temp.attrs['description'] = 'Any notes describing each measurement.'

			# temp = settings.create_dataset('laserpower', data = np.array(data['laserpower']))
			# temp.attrs['description'] = 'Fractional laser power during measurement. Calculated as normalized laser current (max current = 55 A). Laser is operated at steady state.'

			# temp = settings.create_dataset('sattime', data = np.array(data['saturationtime']))
			# temp.attrs['description'] = 'Saturation time for laser/bias conditioning prior to sample measurement. Delay between applying condition and measuring, in seconds.'

			# temp = settings.create_dataset('numIV', data = np.array(data['numIV']))
			# temp.attrs['description'] = 'Number of current/voltage measurements averaged by Kepco when reading IV.'

			# temp = settings.create_dataset('numframes', data = np.array(data['numframes']))
			# temp.attrs['description'] = 'Number of camera frames averaged when taking image.'

			# temp = settings.create_dataset('tempsp', data = np.array(data['temperature_setpoint']))
			# temp.attrs['description'] = 'TEC stage temperature setpoint for each measurement.'

			# calibrations
			calibrations = f.create_group('/calibrations')
			calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

			temp = settings.create_dataset('samplepos', data = np.array(self.__sampleposition))
			temp.attrs['description'] = 'Stage position (um)[x,y] where sample is centered in camera field of view'

			temp = settings.create_dataset('detectorpos', data = np.array(self.__detectorposition))
			temp.attrs['description'] = 'Stage position (um) [x,y] where photodetector is centered in camera field of view'

			temp = settings.create_dataset('camerafov', data = np.array(self.__fov))
			temp.attrs['description'] = 'Camera field of view (um) [x,y]'

			# raw data
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Raw measurements taken during imaging'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Stage x position during measurement. Low x = right side of sample/left side of chamber'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Stage y position during measurement. Low y = top of sample/back of chamber'

			temp = rawdata.create_dataset('img1', data = img1, chunks = True, compression = 'gzip')
			temp.attrs['description'] = 'Raw images acquired for each measurement.'

			temp = rawdata.create_dataset('filter1', data = '550 Longpass'.encode('utf-8'))

			temp = rawdata.create_dataset('img2', data = img2, chunks = True, compression = 'gzip')
			temp.attrs['description'] = 'Raw images acquired for each measurement.'

			temp = rawdata.create_dataset('filter2', data = '720 Longpass'.encode('utf-8'))

			temp = rawdata.create_dataset('temp', data = self.__temperature)
			temp.attrs['description'] = 'Measured TEC stage temperature during measurement. This value is the average of two temperature measurements, just before and after the image/kepco readings/photodetector readings are made. These two values typically span >1 second'

		print('Data saved to {0}'.format(fpath))

		if save_img:
			saveme_0 = (img1*255).astype(int)
			saveme_1 = np.zeros(saveme_0.shape)
			saveme_1[:,:,0] = saveme_0[:,:,2]
			saveme_1[:,:,1] = saveme_0[:,:,1]
			saveme_1[:,:,2] = saveme_0[:,:,0]

			cv2.imwrite(fpath[:-3]+'.tif', saveme_1.astype(int))

		return fpath

	### tile imaging
	def tile(self, samplename, xmin, xmax, numx, ymin, ymax, numy, frames = 10):
		x0, y0 = self.stage.position
		xp = [int(x) for x in np.linspace(x0+xmin, x0+xmax, numx)]
		yp = [int(y) for y in np.linspace(y0+ymin, y0+ymax, numy)]
		ims1 = np.zeros((numy, numx, 1080, 1920, 3))
		ims2 = np.zeros((numy, numx, 1080, 1920, 3))

		self.stage.moveto(x = xp[0], y = yp[0])
		time.sleep(5) #sometimes stage says its done moving too early, expect that on first move which is likely a longer travel time

		flip = False #for snaking. currently always false! backlash in stage makes stitching hard if snaking
		for m, y in tqdm(enumerate(yp), total = numy, desc = 'Y', leave = False):
			if flip:
				flip = False
			else:
				flip = False
			self.stage.moveto(y = y)
			for n, x in tqdm(enumerate(xp), total = numx, desc = 'X', leave = False):
				if flip:
					nn = -n-1
					xx = xp[nn]
				else:
					nn = n
					xx = x
				self.stage.moveto(x = xx)
				ims1[m,nn] = self.cam550.capture(frames)
				ims2[m,nn] = self.cam720.capture(frames)

		self.stage.moveto(x = x0, y = y0)

		self.save(
			samplename,
			ims1,
			ims2, 
			x = xp,
			y = yp,
			note = note,
			save_img = False
			)

	### calibration methods

	def preview(self):
		while(True):
		# Capture frame-by-frame
			ret1, frame1 = self.cam550.cap.read()
			ret2, frame2 = self.cam720.cap.read()

			if ret1 and ret2:
				# Our operations on the frame come here
				# gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

				# Display the resulting frame
				cv2.imshow('550nm lp',cv2.resize(frame1, (800,600)))
				cv2.imshow('720nm lp',cv2.resize(frame2, (800,600)))
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break
		cv2.destroyAllWindows()
	# def findOneSun(self, jsc, area):
	# 	### finds fraction laser power for which measured jsc = target value from solar simulator JV testing.
	# 	# jsc: short circuit current density in mA/cm^2 (positive)
	# 	# area: active area cm^2
	# 	if jsc < 1:
	# 		print('Please provide jsc in units of mA/cm^2, and area in units of cm^2')
	# 		return False

	# 	isc = -jsc * area / 1000 	#negative total current in amps, since kepco will be measuring total photocurrent as amps

	# 	laserpowers = np.linspace(0,1, 7)[1:]	#skip 0, lean on lower end to reduce incident power
	# 	self.kepco.set(voltage = 0)

	# 	laserjsc = np.zeros(len(laserpowers))

	# 	self.laser.set(power = laserpowers[0])		#set to first power before turning on laser
	# 	self.laser.on()
	# 	self.kepco.on()
	# 	for idx, power in enumerate(laserpowers):
	# 		self.laser.set(power = power)
	# 		time.sleep(self.saturationtime)
	# 		_,laserjsc[idx] = self.kepco.read(counts = 25)  
	# 	self.laser.off()
	# 	self.kepco.off()

	# 	#pdb.set_trace()

	# 	pfit = np.polyfit(laserjsc, laserpowers, 2)
	# 	p = np.poly1d(pfit)	#polynomial fit object where x = measured jsc, y = laser power applied
		
	# 	self._sampleOneSun = p(isc)
	# 	self._sampleOneSunSweep = [laserpowers, laserjsc]
	# 	self._sampleOneSunJsc = jsc

	# 	#pdb.set_trace()

	# 	return p(isc), laserpowers, laserjsc	#return laser power to match target jsc

	# def calibrateSpot(self, numx = 21, numy = 21, rngx = None, rngy = None, laserpower = 0.5, export = True):
	# 	### maps an area around the sample FOV, finds the optical power at each point
	# 	print("calibration starting")

	# 	if not self.stage._homed:
	# 		print('Homing stage')
	# 		self.stage.gohome()
	# 	#default calibration area range = camera FOV
	# 	if rngx is None:
	# 		rngx = self.__fov[0]
	# 	if rngy is None:
	# 		rngy = self.__fov[1]

	# 	xpos = np.linspace(self.__detectorposition[0] - (rngx/2), self.__detectorposition[0] + (rngx/2), numx).astype(int)
	# 	ypos = np.linspace(self.__detectorposition[1] - (rngy/2), self.__detectorposition[1] + (rngy/2), numy).astype(int)
		
	# 	self.laser.set(power = laserpower)
	# 	self._spotMap = np.zeros((numy, numx))
	# 	self._spotMapX = xpos
	# 	self._spotMapY = ypos
		
	# 	print('Moving to start position ({0}, {1})'.format(xpos[0], ypos[0]))
	# 	if not self.stage.moveto(x = xpos[0], y = ypos[0]):
	# 		print('Error moving stage to starting position ({0}, {1}) - stage is probably not homed. run method ._stage.gohome()'.format(xpos[0], ypos[0]))		
	# 		return False

	# 	self.laser.on()
	# 	flip = 1
	# 	for m, x in tqdm(enumerate(xpos), desc = 'X', total = len(xpos), leave = False):
	# 		flip = flip * -1
	# 		self.stage.moveto(x = x)
	# 		for n in tqdm(range(len(ypos)), desc = 'Y', total = len(ypos), leave = False):
	# 			if flip > 0:		#use nn instead of n, accounts for snaking between lines
	# 				nn = len(ypos) - n - 1
	# 			else:
	# 				nn = n
	# 			self.stage.moveto(y = ypos[nn])
	# 			self._spotMap[nn,m] = self._getOpticalPower()/100 # suns
	# 	self.laser.off()

	# 	self.stage.moveto(x = self.__sampleposition[0], y = self.__sampleposition[1])	#return stage to camera FOV

	# 	if export:
	# 		self.saveSpotCalibration(note = 'Autosaved by calibrateSpot')

	# def saveSpotCalibration(self, note = ''):
	# 	fids = os.listdir(calibrationfolder)
	# 	sampleNumber = 1
	# 	for fid in fids:
	# 		if 'frgPL_spotCalibration' in fid:
	# 			sampleNumber = sampleNumber + 1

	# 	todaysDate = datetime.datetime.now().strftime('%Y%m%d')
	# 	todaysTime = datetime.datetime.now().strftime('%H:%M:%S')
	# 	fname = 'frgPL_spotCalibration_{0}_{1:04d}.h5'.format(todaysDate, sampleNumber)
	# 	fpath = os.path.join(calibrationfolder, fname)

	# 	## write h5 file

	# 	with h5py.File(fpath, 'w') as f:
	# 		# sample info
	# 		info = f.create_group('/info')
	# 		info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
	# 		# temp = info.create_dataset('name', data = self.sampleName.encode('utf-8'))
	# 		# temp.attrs['description'] = 'Sample name.'
			
	# 		temp = info.create_dataset('notes', data = note.encode())
	# 		temp.attrs['description'] = 'Any notes describing each measurement.'

	# 		temp = info.create_dataset('date', data = todaysDate.encode())
	# 		temp.attrs['description'] = 'Measurement date.'
			
	# 		temp = info.create_dataset('time', data =  todaysTime.encode())
	# 		temp.attrs['description'] = 'Measurement time of day.'


	# 		# calibrations
	# 		calibrations = f.create_group('/calibrations')
	# 		calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

	# 		temp = calibrations.create_dataset('samplepos', data = np.array(self.__sampleposition))
	# 		temp.attrs['description'] = 'Stage position (um)[x,y] where sample is centered in camera field of view'

	# 		temp = calibrations.create_dataset('detectorpos', data = np.array(self.__detectorposition))
	# 		temp.attrs['description'] = 'Stage position (um) [x,y] where photodetector is centered in camera field of view'

	# 		temp = calibrations.create_dataset('camerafov', data = np.array(self.__fov))
	# 		temp.attrs['description'] = 'Camera field of view (um) [x,y]'

	# 		temp = calibrations.create_dataset('spot', data = np.array(self._spotMap))
	# 		temp.attrs['description'] = 'Map [y, x] of incident optical power across camera FOV, can be used to normalize PL images. Laser power set to 0.5 during spot mapping.'

	# 		temp = calibrations.create_dataset('spotx', data = np.array(self._spotMapX))
	# 		temp.attrs['description'] = 'X positions (um) for map of incident optical power across camera FOV, can be used to normalize PL images.'

	# 		temp = calibrations.create_dataset('spoty', data = np.array(self._spotMapY))
	# 		temp.attrs['description'] = 'Y positions (um) for map of incident optical power across camera FOV, can be used to normalize PL images.'

	# 	print('Data saved to {0}'.format(fpath))	

	# def loadSpotCalibration(self, calibrationnumber = None):
	# 	fids = os.listdir(calibrationfolder)
	# 	calnum = []
	# 	for fid in fids:
	# 		if 'frgPL_spotCalibration' in fid:
	# 			calnum.append(int(fid.split('_')[3].split('.')[0]))
	# 		else:
	# 			calnum.append(0)

	# 	if len(calnum) == 0:
	# 		print('Could not find any calibration files! No spotmap loaded')
	# 		return False

	# 	calfile = fids[calnum.index(max(calnum))]	#default to most recent calibration
		
	# 	if calibrationnumber is not None:
	# 		try:
	# 			calfile = fids[calnum.index(calibrationnumber)]
	# 		except:
	# 			print('Could not find calibration {0}: defaulting to most recent calibration {1}'.format(calibrationnumber, max(calnum)))
	# 	fpath = os.path.join(calibrationfolder, calfile)
	# 	## write h5 file

	# 	with h5py.File(fpath, 'r') as f:
	# 		self._spotMap = f['calibrations']['spot'][:]
	# 		self._spotMapX = f['calibrations']['spotx'][:]
	# 		self._spotMapT = f['calibrations']['spoty'][:]

	# 	print('Loaded calibration {0} from {1}.'.format(calnum[fids.index(calfile)], fpath))
	# 	return True

	### group measurement methods

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

	def _backgroundCorrection(self, img):
		img = img - self.__backgroundImage
		img[img<0] = 0

		return img
	#def normalizePL(self):
	### used laser spot power map to normalize PL counts to incident optical power



class Control1:

	def __init__(self,spotmapnumber = None):
		# hardware properties
		self.camid = 0
		self.__temperature = 25	#TEC stage temperature setpoint (C) during measurement
		
		# data saving settings
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputDirectory = os.path.join(root, 'Data', todaysDate)	#default save locations is desktop/frgPL/Data/(todaysDate)
		self.sampleName = None
		self.__dataBuffer = [] # buffer to hold data files during sequential measurements of single sample. Held until a batch export

		# stage/positioning constants
		self.__sampleposition = (39, 90)	#position where TEC stage is centered in camera FOV, mm
		self.__detectorposition = (64, 117)	#absolute position of detector centered in FOV, mm.
		self.__fov = (77, 56)	#dimensions of FOV, mm

		self.connect()
		# self.loadSpotCalibration(spotmapnumber)
	@property
	def temperature(self):
		return self.__temperature

	@temperature.setter
	def temperature(self, t):
		self.tec.setpoint = t
		self.__temperature = t

		

	def connect(self):
		self.cam = Hayear(self.camid)
		# self.camera = FLIR()		# connect to FLIR camera
		# self.kepco = Kepco()		# connect to Kepco
		# self.kepco.set(voltage=0)   # set voltage to 0, seems to solve current compliance issues
		# self.laser = Laser808()		# Connect to OSTECH Laser
		# self.daq = PLDAQ()			# connect to NI-USB6000 DAQ
		self.stage = PLStage(sampleposition = self.__sampleposition)		# connect to FRG stage
		# self.tec = Omega('COM15')			# connect to omega PID controller, which is driving the TEC stage.
		
	def disconnect(self):
		try:
			self.cam.disconnect()
		except:
			print('Could not disconnect camera')

		# try:
		# 	self.kepco.disconnect()
		# except:
		# 	print('Could not disconnect Kepco')
	
		# try:
		# 	self.daq.disconnect()
		# except:
		# 	print('Could not disconnect DAQ')
		try:
			self.stage.disconnect()
		except:
			print('Could not disconnect stage')
		try:
			self.tec.disconnect()
		except:
			print('Could not disconnect TEC controller')


	### basic use functions
	def capture(self, samplename = None, frames = 10, note = '', save_img = False):
		im = self.cam.capture(frames)

		self.save(im,samplename, note, save_img = save_img)


	def save(self, img, samplename = None, note = '', outputdirectory = None, reset = True, save_img = False):

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
			if 'frg_pskPL' in fid:
				sampleNumber = sampleNumber + 1

		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		currentTime = datetime.datetime.now().strftime('%H:%M:%S')
		if self.sampleName is not None:
			fname = 'frg_pskPL_{0}_{1:04d}_{2}.h5'.format(todaysDate, sampleNumber, self.sampleName)
		else:
			fname = 'frg_pskPL_{0}_{1:04d}.h5'.format(todaysDate, sampleNumber)
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

		## write h5 file

		with h5py.File(fpath, 'w') as f:
			# sample info
			info = f.create_group('/info')
			info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
			temp = info.create_dataset('name', data = self.sampleName.encode('utf-8'))
			temp.attrs['description'] = 'Sample name.'
			
			temp = info.create_dataset('notes', data = note.encode('utf-8'))
			temp.attrs['description'] = 'Any notes describing each measurement.'

			temp = info.create_dataset('date', data = todaysDate.encode('utf-8'))
			temp.attrs['description'] = 'Measurement date.'
			
			temp = info.create_dataset('time', data =  currentTime.encode('utf-8'))
			temp.attrs['description'] = 'Measurement time of day.'

			temp = info.create_dataset('numcams', data = 1)
			temp.attrs['description'] = 'Number of cameras employed in setup'


			# # measurement settings
			settings = f.create_group('/settings')
			settings.attrs['description'] = 'Settings used for measurements.'

			# temp = settings.create_dataset('vbias', data = np.array(data['bias']))
			# temp.attrs['description'] = 'Nominal voltage bias set by Kepco during measurement.'

			# temp = settings.create_dataset('notes', data = np.array([x.encode('utf-8') for x in data['note']]))
			# temp.attrs['description'] = 'Any notes describing each measurement.'

			# temp = settings.create_dataset('laserpower', data = np.array(data['laserpower']))
			# temp.attrs['description'] = 'Fractional laser power during measurement. Calculated as normalized laser current (max current = 55 A). Laser is operated at steady state.'

			# temp = settings.create_dataset('sattime', data = np.array(data['saturationtime']))
			# temp.attrs['description'] = 'Saturation time for laser/bias conditioning prior to sample measurement. Delay between applying condition and measuring, in seconds.'

			# temp = settings.create_dataset('numIV', data = np.array(data['numIV']))
			# temp.attrs['description'] = 'Number of current/voltage measurements averaged by Kepco when reading IV.'

			# temp = settings.create_dataset('numframes', data = np.array(data['numframes']))
			# temp.attrs['description'] = 'Number of camera frames averaged when taking image.'

			# temp = settings.create_dataset('tempsp', data = np.array(data['temperature_setpoint']))
			# temp.attrs['description'] = 'TEC stage temperature setpoint for each measurement.'


			if self.stage.position[0] is None:
				stagepos = self.__sampleposition
			else:
				stagepos = self.stage.position

			temp = settings.create_dataset('position', data = np.array(stagepos))
			temp.attrs['description'] = 'Stage position during measurement.'

			# calibrations
			calibrations = f.create_group('/calibrations')
			calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

			temp = settings.create_dataset('samplepos', data = np.array(self.__sampleposition))
			temp.attrs['description'] = 'Stage position (um)[x,y] where sample is centered in camera field of view'

			temp = settings.create_dataset('detectorpos', data = np.array(self.__detectorposition))
			temp.attrs['description'] = 'Stage position (um) [x,y] where photodetector is centered in camera field of view'

			temp = settings.create_dataset('camerafov', data = np.array(self.__fov))
			temp.attrs['description'] = 'Camera field of view (um) [x,y]'

			# raw data
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Raw measurements taken during imaging'

			temp = rawdata.create_dataset('img', data = img, chunks = True, compression = 'gzip')
			temp.attrs['description'] = 'Raw images acquired for each measurement.'

			temp = rawdata.create_dataset('filter', data = '500 Longpass'.encode('utf-8'))

			
			temp = rawdata.create_dataset('temp', data = self.__temperature)
			temp.attrs['description'] = 'Measured TEC stage temperature during measurement. This value is the average of two temperature measurements, just before and after the image/kepco readings/photodetector readings are made. These two values typically span >1 second'

		print('Data saved to {0}'.format(fpath))

		if save_img:
			saveme_0 = (img1*255).astype(int)
			saveme_1 = np.zeros(saveme_0.shape)
			saveme_1[:,:,0] = saveme_0[:,:,2]
			saveme_1[:,:,1] = saveme_0[:,:,1]
			saveme_1[:,:,2] = saveme_0[:,:,0]

			cv2.imwrite(fpath[:-3]+'.tif', saveme_1.astype(int))

		return fpath

	### tile imaging
	def tileImages(self, xmin, xmax, numx, ymin, ymax, numy, frames = 100):
		x0, y0 = self.stage.position
		xp = [int(x) for x in np.linspace(x0+xmin, x0+xmax, numx)]
		yp = [int(y) for y in np.linspace(y0+ymin, y0+ymax, numy)]
		ims1 = np.zeros((numy, numx, 1080, 1920, 3))
		ims2 = np.zeros((numy, numx, 1080, 1920, 3))

		self.stage.moveto(x = xp[0], y = yp[0])
		time.sleep(5) #sometimes stage says its done moving too early, expect that on first move which is likely a longer travel time

		flip = False #for snaking
		for m, y in tqdm(enumerate(yp), total = numy, desc = 'Y', leave = False):
			if flip:
				flip = False
			else:
				flip = False
			self.stage.moveto(y = y)
			for n, x in tqdm(enumerate(xp), total = numx, desc = 'X', leave = False):
				if flip:
					nn = -n-1
					xx = xp[nn]
				else:
					nn = n
					xx = x
				self.stage.moveto(x = xx)
				ims1[m,nn] = self.cam550.capture(frames)
				ims2[m,nn] = self.cam550.capture(frames)

		self.stage.moveto(x = x0, y = y0)
		return ims1, ims2, xp, yp

	### calibration methods

	def preview(self):
		while(True):
		# Capture frame-by-frame
			ret1, frame1 = self.cam550.cap.read()
			ret2, frame2 = self.cam720.cap.read()

			if ret1 and ret2:
				# Our operations on the frame come here
				# gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

				# Display the resulting frame
				cv2.imshow('550nm lp',cv2.resize(frame1, (800,600)))
				cv2.imshow('720nm lp',cv2.resize(frame2, (800,600)))
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break
		cv2.destroyAllWindows()
	# def findOneSun(self, jsc, area):
	# 	### finds fraction laser power for which measured jsc = target value from solar simulator JV testing.
	# 	# jsc: short circuit current density in mA/cm^2 (positive)
	# 	# area: active area cm^2
	# 	if jsc < 1:
	# 		print('Please provide jsc in units of mA/cm^2, and area in units of cm^2')
	# 		return False

	# 	isc = -jsc * area / 1000 	#negative total current in amps, since kepco will be measuring total photocurrent as amps

	# 	laserpowers = np.linspace(0,1, 7)[1:]	#skip 0, lean on lower end to reduce incident power
	# 	self.kepco.set(voltage = 0)

	# 	laserjsc = np.zeros(len(laserpowers))

	# 	self.laser.set(power = laserpowers[0])		#set to first power before turning on laser
	# 	self.laser.on()
	# 	self.kepco.on()
	# 	for idx, power in enumerate(laserpowers):
	# 		self.laser.set(power = power)
	# 		time.sleep(self.saturationtime)
	# 		_,laserjsc[idx] = self.kepco.read(counts = 25)  
	# 	self.laser.off()
	# 	self.kepco.off()

	# 	#pdb.set_trace()

	# 	pfit = np.polyfit(laserjsc, laserpowers, 2)
	# 	p = np.poly1d(pfit)	#polynomial fit object where x = measured jsc, y = laser power applied
		
	# 	self._sampleOneSun = p(isc)
	# 	self._sampleOneSunSweep = [laserpowers, laserjsc]
	# 	self._sampleOneSunJsc = jsc

	# 	#pdb.set_trace()

	# 	return p(isc), laserpowers, laserjsc	#return laser power to match target jsc

	# def calibrateSpot(self, numx = 21, numy = 21, rngx = None, rngy = None, laserpower = 0.5, export = True):
	# 	### maps an area around the sample FOV, finds the optical power at each point
	# 	print("calibration starting")

	# 	if not self.stage._homed:
	# 		print('Homing stage')
	# 		self.stage.gohome()
	# 	#default calibration area range = camera FOV
	# 	if rngx is None:
	# 		rngx = self.__fov[0]
	# 	if rngy is None:
	# 		rngy = self.__fov[1]

	# 	xpos = np.linspace(self.__detectorposition[0] - (rngx/2), self.__detectorposition[0] + (rngx/2), numx).astype(int)
	# 	ypos = np.linspace(self.__detectorposition[1] - (rngy/2), self.__detectorposition[1] + (rngy/2), numy).astype(int)
		
	# 	self.laser.set(power = laserpower)
	# 	self._spotMap = np.zeros((numy, numx))
	# 	self._spotMapX = xpos
	# 	self._spotMapY = ypos
		
	# 	print('Moving to start position ({0}, {1})'.format(xpos[0], ypos[0]))
	# 	if not self.stage.moveto(x = xpos[0], y = ypos[0]):
	# 		print('Error moving stage to starting position ({0}, {1}) - stage is probably not homed. run method ._stage.gohome()'.format(xpos[0], ypos[0]))		
	# 		return False

	# 	self.laser.on()
	# 	flip = 1
	# 	for m, x in tqdm(enumerate(xpos), desc = 'X', total = len(xpos), leave = False):
	# 		flip = flip * -1
	# 		self.stage.moveto(x = x)
	# 		for n in tqdm(range(len(ypos)), desc = 'Y', total = len(ypos), leave = False):
	# 			if flip > 0:		#use nn instead of n, accounts for snaking between lines
	# 				nn = len(ypos) - n - 1
	# 			else:
	# 				nn = n
	# 			self.stage.moveto(y = ypos[nn])
	# 			self._spotMap[nn,m] = self._getOpticalPower()/100 # suns
	# 	self.laser.off()

	# 	self.stage.moveto(x = self.__sampleposition[0], y = self.__sampleposition[1])	#return stage to camera FOV

	# 	if export:
	# 		self.saveSpotCalibration(note = 'Autosaved by calibrateSpot')

	# def saveSpotCalibration(self, note = ''):
	# 	fids = os.listdir(calibrationfolder)
	# 	sampleNumber = 1
	# 	for fid in fids:
	# 		if 'frgPL_spotCalibration' in fid:
	# 			sampleNumber = sampleNumber + 1

	# 	todaysDate = datetime.datetime.now().strftime('%Y%m%d')
	# 	todaysTime = datetime.datetime.now().strftime('%H:%M:%S')
	# 	fname = 'frgPL_spotCalibration_{0}_{1:04d}.h5'.format(todaysDate, sampleNumber)
	# 	fpath = os.path.join(calibrationfolder, fname)

	# 	## write h5 file

	# 	with h5py.File(fpath, 'w') as f:
	# 		# sample info
	# 		info = f.create_group('/info')
	# 		info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
	# 		# temp = info.create_dataset('name', data = self.sampleName.encode('utf-8'))
	# 		# temp.attrs['description'] = 'Sample name.'
			
	# 		temp = info.create_dataset('notes', data = note.encode())
	# 		temp.attrs['description'] = 'Any notes describing each measurement.'

	# 		temp = info.create_dataset('date', data = todaysDate.encode())
	# 		temp.attrs['description'] = 'Measurement date.'
			
	# 		temp = info.create_dataset('time', data =  todaysTime.encode())
	# 		temp.attrs['description'] = 'Measurement time of day.'


	# 		# calibrations
	# 		calibrations = f.create_group('/calibrations')
	# 		calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

	# 		temp = calibrations.create_dataset('samplepos', data = np.array(self.__sampleposition))
	# 		temp.attrs['description'] = 'Stage position (um)[x,y] where sample is centered in camera field of view'

	# 		temp = calibrations.create_dataset('detectorpos', data = np.array(self.__detectorposition))
	# 		temp.attrs['description'] = 'Stage position (um) [x,y] where photodetector is centered in camera field of view'

	# 		temp = calibrations.create_dataset('camerafov', data = np.array(self.__fov))
	# 		temp.attrs['description'] = 'Camera field of view (um) [x,y]'

	# 		temp = calibrations.create_dataset('spot', data = np.array(self._spotMap))
	# 		temp.attrs['description'] = 'Map [y, x] of incident optical power across camera FOV, can be used to normalize PL images. Laser power set to 0.5 during spot mapping.'

	# 		temp = calibrations.create_dataset('spotx', data = np.array(self._spotMapX))
	# 		temp.attrs['description'] = 'X positions (um) for map of incident optical power across camera FOV, can be used to normalize PL images.'

	# 		temp = calibrations.create_dataset('spoty', data = np.array(self._spotMapY))
	# 		temp.attrs['description'] = 'Y positions (um) for map of incident optical power across camera FOV, can be used to normalize PL images.'

	# 	print('Data saved to {0}'.format(fpath))	

	# def loadSpotCalibration(self, calibrationnumber = None):
	# 	fids = os.listdir(calibrationfolder)
	# 	calnum = []
	# 	for fid in fids:
	# 		if 'frgPL_spotCalibration' in fid:
	# 			calnum.append(int(fid.split('_')[3].split('.')[0]))
	# 		else:
	# 			calnum.append(0)

	# 	if len(calnum) == 0:
	# 		print('Could not find any calibration files! No spotmap loaded')
	# 		return False

	# 	calfile = fids[calnum.index(max(calnum))]	#default to most recent calibration
		
	# 	if calibrationnumber is not None:
	# 		try:
	# 			calfile = fids[calnum.index(calibrationnumber)]
	# 		except:
	# 			print('Could not find calibration {0}: defaulting to most recent calibration {1}'.format(calibrationnumber, max(calnum)))
	# 	fpath = os.path.join(calibrationfolder, calfile)
	# 	## write h5 file

	# 	with h5py.File(fpath, 'r') as f:
	# 		self._spotMap = f['calibrations']['spot'][:]
	# 		self._spotMapX = f['calibrations']['spotx'][:]
	# 		self._spotMapT = f['calibrations']['spoty'][:]

	# 	print('Loaded calibration {0} from {1}.'.format(calnum[fids.index(calfile)], fpath))
	# 	return True

	### group measurement methods

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

	def _backgroundCorrection(self, img):
		img = img - self.__backgroundImage
		img[img<0] = 0

		return img
	#def normalizePL(self):
	### used laser spot power map to normalize PL counts to incident optical power
