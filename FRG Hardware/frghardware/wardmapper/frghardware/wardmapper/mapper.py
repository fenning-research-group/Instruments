import numpy as np
import matplotlib.pyplot as plt
import os
import serial
import time
import json
import datetime
from frghardware.components.stage import Thorlabs_LTS150_xy
from frghardware.components.mono import Mono
from frghardware.components.daq import DAQ
import datetime
from tqdm import tqdm
import h5py
import threading
from frghardware.components.nkt import Compact, Select
from frghardware.components.tec import Omega
from pymeasure.instruments.srs import SR830
root = 'D:\\frgmapper'
if not os.path.exists(root):
	os.mkdir(root)
datafolder = os.path.join(root, 'Data')
if not os.path.exists(datafolder):
	os.mkdir(datafolder)

DEFAULT_FLUSH_INTERVAL = 10
### Settings for different PDA10DT Bandwidths:

# 1k: 
#		daq.countsPulseDuration = 50
#		daq.countsPerTrigger = 100
#		compact.setPulseFrequency(495)
#
# 10k:
#		daq.countsPulseDuration = 20
#		daq.countsPerTrigger = 30
#		compact.setPulseFrequency(1665)


class controlGeneric(object):
	def __init__(self, dwelltime = 0.2):
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputdir = os.path.join(root, datafolder, todaysDate)
		self.__hardwareSetup = 'mono'		#distinguish whether saved data comes from the mono or nkt setup
		self.__dwelltime = dwelltime
		self.__baselineTaken = False
		self.__baseline = {}
		self.__flushinterval = DEFAULT_FLUSH_INTERVAL
		self.__flushcounter = 0
		plt.ion()	#make plots of results non-blocking

	@property
	def dwelltime(self):
		return self.__dwelltime

	@dwelltime.setter
	def dwelltime(self, x):
		# sets daq counts to match desired measurement time (x, in seconds)
		self.daq.dwelltime = x
		self.__dwelltime = x

	# user methods
	def generatewavelengths(self, wmin = 1700, wmax = 2000, wsteps = 151):
		wavelengths = np.linspace(wmin, wmax, wsteps)
		return wavelengths

	def takebaseline(self, wavelengths):
		self.__flushinterval = np.inf
		# clean up wavelengths input
		wavelengths = np.array(wavelengths)

		#light baseline
		self.__baseline['Wavelengths'] = wavelengths
		self.__baseline['LightRaw'], self.__baseline['LightRefRaw']  = self._scanroutine(wavelengths)
		try:
			self.__baseline['Light'] = np.divide(self.__baseline['LightRaw'], self.__baseline['LightRefRaw'])
		except:
			print(self.__baseline['LightRaw'])
			print(self.__baseline['LightRefRaw'])

		#dark baseline
		# if not self.processPulseTrain:
		storeddwelltime = self.__dwelltime
		storedUseExtClock = self.daq.useExtClock
		self.dwelltime = 5	#take a long acquisition for the dark baseline, as it is a single point measurement
		self.daq.useExtClock = False
		out = self.daq.read()
		self.dwelltime = storeddwelltime
		self.daq.useExtClock = storedUseExtClock

		self.__baseline['DarkRaw'] = out['IntSphere']['Mean']
		self.__baseline['DarkRefRaw'] = out['Reference']['Mean']
		self.__baseline['Dark'] = self.__baseline['DarkRaw'] / self.__baseline['DarkRefRaw']

		self.__baselineTaken = True
		self.__flushinterval = DEFAULT_FLUSH_INTERVAL

	def scanpoint(self, label, wavelengths = None):
		def preparefile(f):
			dummy1d = np.full(wavelengths.shape, np.nan)

			info, settings, baseline, completed = self._save_generic(f, label = label, scantype = 'scanpoint')

			# raw data
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during point scan.'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned.'

			reflectance = rawdata.create_dataset('reflectance', data = dummy1d)
			reflectance.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as fraction (0-1), not percent!'

			signal = rawdata.create_dataset('signalRaw', data = dummy1d)
			signal.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			reference = rawdata.create_dataset('referenceRaw', data = dummy1d)
			reference.attrs['description'] = 'Raw signal for reference detector. (V)'

			f.swmr_mode = True # Single Writer Multiple Reader, allows h5 file to be read during scan.
			f.flush()

			return signal, reference, reflectance, completed

		wavelengths = self._cleanwavelengthinput(wavelengths)
		fpath = self._getsavepath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as self.f:
			signal, reference, reflectance, completed = preparefile(self.f)

			self.__flushcounter = 0
			self.__flushinterval = 5
			signal[()], reference[()] = self._scanroutine(wavelengths)
			self.__flushinterval = DEFAULT_FLUSH_INTERVAL
			reflectance[()] = self._baselinecorrectionroutine(wavelengths, signal, reference)

<<<<<<< Updated upstream
			completed = 1

=======
>>>>>>> Stashed changes
	def scanline(self, label, axis, pmin, pmax, steps, wavelengths = None, p0 = None):
		def preparefile(f):
			dummy1d =  np.full((steps, ), np.nan)
			dummy2d =  np.full((steps, len(wavelengths)), np.nan)

			if axis == 'x':
				idlepos = self.stage.position[1]
				idleaxis = 'y'
			else:
				idlepos = self.stage.position[0]
				idleaxis = 'x'


			info, settings, baseline, completed = self._save_generic(f, label = label, scantype = 'scanline')

			## add scan parameters to settings
			temp = settings.create_dataset('num', data = np.array(allpts.shape[0]))
			temp.attrs['description'] = f'Number of points scanned in {axis}'			

			stepsize = np.abs(allpts[1] - allpts[0])

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Step size (mm) in line scan.'	

			temp = settings.create_dataset('axis', data = axis.encode('utf-8'))
			temp.attrs['description'] = 'Axis scanned (x or y)'

			temp = settings.create_dataset('idle_axis', data = idle_axis.encode('utf-8'))
			temp.attrs['description'] = 'Axis not scanned (x or y)'

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('idle_pos', data = idlepos)
			temp.attrs['description'] = f'{idleaxis} coordinate, did not change throughout line scan'

			temp = rawdata.create_dataset('pos', data = np.array(allpts))
			temp.attrs['description'] = f'Absolute {axis} coordinate (mm) per point'

			temp = rawdata.create_dataset('relpos', data = np.array(allpts - np.min(allpts)))
			temp.attrs['description'] = f'Relative {axis} coordinate (mm) per point'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			reflectance = rawdata.create_dataset('reflectance', data = dummy2d)
			reflectance.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			signal = rawdata.create_dataset('signalRaw', data = dummy2d)
			signal.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			reference = rawdata.create_dataset('referenceRaw', data = dummy2d)
			reference.attrs['description'] = 'Raw signal for reference detector. (V)'

			delay = rawdata.create_dataset('delay', data = dummy1d)
			delay.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			f.swmr_mode = True # Single Writer Multiple Reader, allows h5 file to be read during scan.
			f.flush()

			return reflectance, signal, reference, delay, completed

		wavelengths = self._cleanwavelengthinput(wavelengths)

		if str.lower(axis) == 'x':
			axis = 'x'
			idle_axis = 'y'
		elif str.lower(axis) == 'y':
			axis = 'y'
			idle_axis = 'x'
		else:
			print('Error: axis must equal \'x\' or \'y\': user provided {0}'.format(axis))
			return

		x0, y0 = self.stage.position #if no p0 specified, assume coordinates are relative to current position
		if p0 is None:
			if axis == 'x':
				p0 = x0
			else:
				p0 = y0

		allpts = np.linspace(p0 + pmin, p0 + pmax, steps) #coordinates are relative to center coordinate p0
		if axis == 'x':
			xval = allpts
			yval = y0
		else:
			xval = x0,
			yval = allpts

		fpath = self._getsavepath(label = label)	#generate filepath for saving data
		self.__flushcounter = 0
		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as self.f:
			reflectance, signal, reference, delay, completed = preparefile(self.f)

			firstscan = True
			lastscan = False
			startTime = time.time()
			for idx, p in tqdm(enumerate(allpts), desc = 'Scanning {0}'.format(axis), total = steps, leave = False):
				if idx == steps-1:
					lastScan = True

				if axis == 'x':
					moveThread = threading.Thread(target = self.stage.moveto, args = (p, y0))
				else:
					moveThread = threading.Thread(target = self.stage.moveto, args = (x0, p))
				moveThread.start()
				wlThread = threading.Thread(target = self._goToWavelength, args = (wavelengths[0],))
				wlThread.start()
				moveThread.join()
				wlThread.join()

				signal[idx, :], reference[idx, :] = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
				reflectance[idx, :] = self._baselinecorrectionroutine(wavelengths, signal[idx, :], reference[idx, :])
				delay[idx] = time.time() - startTime #time in seconds since scan began

				firstscan = False

			completed = 1
		self.stage.moveto(x = x0, y = y0)	#go back to map center position
		self._lightOff()

	def findarea(self, wavelength, xsize = 30, ysize = 30, xsteps = 40, ysteps = 40, plot = True, export = False):
		### method to find sample edges. does two line scans in a cross over the sample at a single wavelength.
		# clean up wavelengths input
		self.__flushinterval = np.inf

		wavelength = self._cleanwavelengthinput(wavelength)

		if wavelength.shape[0] > 1:
			print('Please use a single wavelength for findarea - aborting')
			return False
		
		# self.stage.gotocenter() #go to center position, where sample is centered on integrating sphere port. Might need to remove this line later if inconvenient
		x0, y0 = self.stage.position

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)
		

		self._goToWavelength(wavelength[0])

		self._lightOn()	
		self.stage.moveto(x = allx[0], y = y0)
		xdata = np.zeros((xsteps,))
		for idx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			self.stage.moveto(x = x)
			out = self.daq.read()
			signal = [out['IntSphere']['Mean']]
			ref = [out['Reference']['Mean']]
			xdata[idx] = self._baselinecorrectionroutine(wavelengths = wavelength, signal = signal, reference = ref)
		self._lightOff()

		self.stage.moveto(x = x0, y = ally[0])
		self._lightOn()
		ydata = np.zeros((ysteps,))
		for idx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
			self.stage.moveto(y = y)
			out = self.daq.read()
			signal = [out['IntSphere']['Mean']]
			ref = [out['Reference']['Mean']]
			ydata[idx]= self._baselinecorrectionroutine(wavelengths = wavelength, signal = signal, reference = ref)
		self._lightOff()
		self.stage.moveto(x = x0, y = y0) #return to original position

		center = [None, None]
		size = [None, None]
		if plot:
			fig, ax = plt.subplots(2,1)
			# ax[0].plot(allx, xdata)
			center[0], size[0] = self._findedges(allx, xdata, ax = ax[0])
			ax[0].set_xlabel('X Position (mm)')
			ax[0].set_ylabel('Reflectance at {0} nm'.format(wavelength[0]))
			ax[0].set_title('X Scan')

			# ax[1].plot(ally, ydata)
			center[1], size[1] = self._findedges(ally, ydata, ax = ax[1])
			ax[1].set_xlabel('Y Position (mm)')
			ax[1].set_ylabel('Reflectance at {0} nm'.format(wavelength[0]))
			ax[1].set_title('Y Scan')
			plt.tight_layout()
			plt.show()
		# print + return the centroid, width/bounds if found (currently no sanity checking to see if bounds are realistic, rely on user to judge the plots for themselves)
		print('Suggested scanarea parameters:\n\tx0 = {0}\n\ty0 = {1}\n\txsize = {2}\n\tysize = {3}\n'.format(center[0], center[1], size[0], size[1]))

		self.__flushinterval = DEFAULT_FLUSH_INTERVAL
		return center, size

	def scanarea(self, label, xmin, xmax, xsteps, ymin, ymax, ysteps, wavelengths = None, x0 = None, y0 = None, export = True):
		def preparefile(f):
			dummy2d =  np.full((ysteps, xsteps), np.nan)
			dummy3d =  np.full((ysteps, xsteps, len(wavelengths)), np.nan)

			info, settings, baseline, completed = self._save_generic(f, label = label, scantype = 'scanarea')

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(allx.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(ally.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('rangex', data = np.array(np.abs(allx[-1] - allx[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(ally[-1] - ally[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if allx.shape[0] > 1:
				stepsize = stepsize + np.abs(allx[1] - allx[0])
				countedaxes = countedaxes + 1
			if ally.shape[0] > 1:
				stepsize = stepsize + np.abs(ally[1] - ally[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0 '			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(allx))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y', data = np.array(ally))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(allx - np.min(allx)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely', data = np.array(ally - np.min(ally)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			reflectance = rawdata.create_dataset('reflectance', data = dummy3d)
			reflectance.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			signal = rawdata.create_dataset('signalRaw', data = dummy3d)
			signal.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			reference = rawdata.create_dataset('referenceRaw', data = dummy3d)
			reference.attrs['description'] = 'Raw signal for reference detector. (V)'

			delay = rawdata.create_dataset('delay', data = dummy2d)
			delay.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'	

			f.swmr_mode = True # Single Writer Multiple Reader, allows h5 file to be read during scan.

			return reflectance, signal, reference, delay, completed

		# clean up wavelengths input
		wavelengths = self._cleanwavelengthinput(wavelengths)

		currentx, currenty = self.stage.position # unless otherwise specified, assume center coordinates x0,y0 are current position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		allx = np.linspace(x0 + xmin, x0 + xmax, xsteps)
		ally = np.linspace(y0 + ymin, y0 + ymax, ysteps)


		fpath = self._getsavepath(label = label)	#generate filepath for saving data
		self.__flushcounter = 0
		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as self.f:
			reflectance, signal, reference, delay, completed = preparefile(self.f)

			firstscan = True
			lastscan = False
			reverse= -1 # for snaking
			startTime = time.time()
			for yidx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
				reverse=reverse*(-1)
				for xidx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
					if xidx == xsteps-1 and yidx == ysteps-1:
						lastScan = True
					# Condition to map in a snake pattern rather than coming back to first x point
					wlThread = threading.Thread(target = self._goToWavelength, args = (wavelengths[0],))
					wlThread.start()

					if reverse > 0: #snaking in x dimension
						xidx_ = xidx
						x_ = x
					else:
						xidx_ = xsteps-1-xidx
						x_ = allx[xidx_]

					moveThread = threading.Thread(target = self.stage.moveto, args = (x_, y))
					moveThread.start()
					wlThread.join()
					moveThread.join()

					signal[yidx, xidx_, :], reference[yidx, xidx_, :] = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					reflectance[yidx, xidx_, :] = self._baselinecorrectionroutine(wavelengths, signal[yidx, xidx_, :], reference[yidx, xidx_, :])
					delay[yidx, xidx_] = time.time() - startTime #time in seconds since scan began
				
					firstscan = False

			completed = 1

		self.stage.moveto(x = x0, y = y0)	#go back to map center position
		self._lightOff()

	def flyscanarea(self, label, xsize, ysize, wavelengths = None, xsteps = 21, ysteps = 21, x0 = None, y0 = None, export = True):
		# clean up wavelengths input
		wavelengths = self._cleanwavelengthinput(wavelengths)

		currentx, currenty = self.stage.position # return position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((ysteps, xsteps, len(wavelengths)))
		delay = np.zeros((len(wavelengths), yidx))

		firstscan = True
		lastscan = False
		reverse= -1 # for snaking
		startTime = time.time()
		for wlidx, wl in tqdm(enumerate(wavelengths), desc = 'Wavelength', total = wavelengths.shape[0], leave = False):
			self.stage.moveto(x = allx[0], y = ally[0])	#move to starting position for each subsequent wavelength map
			self._goToWavelength(wl)	#set the correct wavelength
			for yidx, y in tqdm(enumerate(ally), desc = 'Flyscan Lines', total = ally.shape[0], leave = False):
				self.stage.moveto(y = y)	#move to next line
				if (yidx == ally.shape[0]) and (wlidx == wavelengths.shape[0]):
					lastscan = True

				reverse = reverse*(-1)
				if reverse > 0: #go in the forward direction
					linedata, linetime, linesignal, linereference = self._flyscanroutine(wavelength = wl, 
						x0 = allx[0], 
						x1 = allx[-1], 
						numpts = allx.shape[0], 
						firstscan = firstscan, 
						lastscan = lastscan
						)
				else: # go in the reverse direction
					linedata, linetime, linesignal, linereference = self._flyscanroutine(wavelength = wl, 
						x0 = allx[0], 
						x1 = allx[-1], 
						numpts = allx.shape[0], 
						firstscan = firstscan, 
						lastscan = lastscan
						)
					linedata = np.flipud(linedata)
				
				data[yidx,:,wlidx] = linedata
				delay[wlidx, yidx] = time.time() - startTime #time in seconds since scan began
				firstscan = False

		self.stage.moveto(x = x0, y = y0)	#go back to map center position

		if export:
			# export as a hfile
			self._save_flyscanarea(label = label, 
				x = allx, 
				y = ally, 
				delay = delay, 
				wavelengths = wavelengths, 
				reflectance = data
				)

	def timeseries(self, label, duration, interval, wavelengths = None, logtemperature = False, export = True):
		### records a reflectance spectrum for a given duration (seconds) at set intervals (seconds)
		#	TODO: I don't think this will work for single wavelength inputs

		# clean up wavelengths input
		def preparefile(f):
			dummy1d =  np.full((0,), np.nan)
			dummy2d =  np.full((0, len(wavelengths)), np.nan)


			info, settings, baseline, completed = self._save_generic(f, label = label, scantype = 'timeseries')		

			## add scan parameters to settings
			temp = settings.create_dataset('duration', data = np.array(duration))
			temp.attrs['description'] = 'Total time (s) desired for time series.'			

			temp = settings.create_dataset('interval', data = np.array(interval))
			temp.attrs['description'] = 'Time (s) desired between subsequent scans.'

			if logtemperature:
				temp = settings.create_dataset('temperatureLogged', data = 1)
			else:
				temp = settings.create_dataset('temperatureLogged', data = 0)
			temp.attrs['description'] = 'Temperature logged during measurements. Note that this is the temperature of the heating pad in slot 2, actual sample temperature may vary.'

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			reflectance = rawdata.create_dataset('reflectance', data = dummy2d, maxshape = (None,len(wavelengths)))
			reflectance.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [timestep, wl]. Stored as fraction (0-1), not percent!'
			
			signal = rawdata.create_dataset('signalRaw', data = dummy2d, maxshape = (None, len(wavelengths)))
			signal.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			reference = rawdata.create_dataset('referenceRaw', data = dummy2d, maxshape = (None, len(wavelengths)))
			reference.attrs['description'] = 'Raw signal for reference detector. (V)'
			
			delay = rawdata.create_dataset('delay', data = dummy1d, maxshape = (None, ))
			delay.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			temperature = rawdata.create_dataset('temperature', data = dummy1d, maxshape = (None, ))
			temperature.attrs['description'] = 'Temperature (C) of heating pad in slot 2 at the time that each scan was acquired at.'

			f.swmr_mode = True # Single Writer Multiple Reader, allows h5 file to be read during scan.
			f.flush()
			
			return reflectance, signal, reference, delay, temperature, completed

		def h5_extend_append(dset, data):
			'''
			timeseries has an undetermined number of datapoints. this function
			appends data to the h5 datasets.
			'''
			rows = dset.shape[0]
			dset.resize(rows + 1, axis = 0)
			dset[-1] = data

		if logtemperature:
			print('Note: Temperature control/logging is only valid on slot 2!')

		wavelengths = self._cleanwavelengthinput(wavelengths)
		startTime = time.time()
		pbarPercent = 0
		fpath = self._getsavepath(label = label)	#generate filepath for saving data
		self.__flushcounter = 0
		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as self.f:
			reflectance, signal, reference, delay, temperature, completed = preparefile(self.f)
			with tqdm(total = 100, desc = 'Scanning every {0} s for {1} s'.format(interval, duration), leave = False) as pbar:
				while (time.time() - startTime) <= duration:
					if (time.time()-startTime) >= (interval*len(delay)):	#time for the next scan
						h5_extend_append(delay, time.time() - startTime)
						if logtemperature:
							h5_extend_append(temperature, self.heater.getTemperature())
						sig, ref = self._scanroutine(wavelengths, lastscan = False)
						h5_extend_append(reflectance, self._baselinecorrectionroutine(wavelengths, sig, ref))
						h5_extend_append(signal, sig)
						h5_extend_append(reference, ref)
						self.f.flush() #flush after every scan
					else:	#if we have some time to wait between scans, close the shutter and go to the starting wavelength
						self._lightOff()
						self._goToWavelength(wavelength = wavelengths[0])
					
					currentPercent = round(100*(time.time()-startTime)/duration)
					if currentPercent > 100:
							currentPercent = 100

					if currentPercent > pbarPercent:
						pbar.update(currentPercent - pbarPercent)
						pbarPercent = currentPercent

					time.sleep(interval/100)	#we can hit our interval within 1% accuracy, but give the cpu some rest
			
			completed = 1
		self._lightOff()
	
	def scanareaWaRD(self, label, wavelengths, wavelengths_full = None, xsize = 52, ysize = 52, xsteps = 53, ysteps = 53, x0 = None, y0 = None, position = None, export = True):
		x0s = [33, 106, 106, 33]	## UPDATE PROPER LOCATIONS
		y0s = [117,117,57.5,57.5]

		fullScanCoordinates = [		#spiral pattern to sample pts at varying distance from map center
			[2,28],
			[15,2],
			[19,14],
			[19,28],
			[23,43],
			[26,26],
			[28,23],
			[36,30],
			[41,12],
			[49,31]
		]

		if position is not None:
			if position < 1 or position > 4:
				print('Error: Position must hold a value from 1-4. User provided {0}. Scanning centered at current stage position'.format(position))
			else:
				x0 = x0s[position-1]
				y0 = y0s[position-1]

		currentx, currenty = self.stage.position # return position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		wavelengths = self._cleanwavelengthinput(wavelengths)
		if wavelengths_full is not None:
			wavelengths_full = self._cleanwavelengthinput(wavelengths_full)
		else:
			wavelengths_full = np.linspace(1700, 2000, 151).astype(int)

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((ysteps, xsteps, len(wavelengths)))
		signal = np.zeros((ysteps, xsteps, len(wavelengths)))
		reference = np.zeros((ysteps, xsteps, len(wavelengths)))
		delay = np.zeros((ysteps, xsteps))

		data_full = np.zeros((len(fullScanCoordinates), len(wavelengths_full)))
		signal_full = np.zeros((len(fullScanCoordinates), len(wavelengths_full)))
		reference_full = np.zeros((len(fullScanCoordinates), len(wavelengths_full)))
		delay_full = np.zeros((len(fullScanCoordinates),))
		x_full = np.zeros((len(fullScanCoordinates),))
		y_full = np.zeros((len(fullScanCoordinates),))

		fullScanIdx = 0

		firstscan = True
		lastscan = False
		reverse= -1 # for snaking
		startTime = time.time()
		for xidx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			reverse=reverse*(-1)
			for yidx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
				if xidx == xsteps-1 and yidx == ysteps-1:
					lastScan = True
				# Condition to map in a snake pattern rather than coming back to first x point
				wlThread = threading.Thread(target = self._goToWavelength, args = (wavelengths[0],))
				wlThread.start()

				if reverse > 0: #go in the forward direction
					yyidx = yidx
				else:			# go in reverse direction
					yyidx = ysteps-1-yidx

				moveThread = threading.Thread(target = self.stage.moveto, args = (x, ally[yyidx]))
				moveThread.start()
				wlThread.join()
				moveThread.join()

				signal[yyidx, xidx, :], reference[yyidx, xidx, :], _ = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
				data[yyidx, xidx, :] = self._baselinecorrectionroutine(wavelengths, signal[yyidx, xidx, :], reference[yyidx, xidx, :])
				delay[yyidx, xidx] = time.time() - startTime #time in seconds since scan began
				firstscan = False

				if [yyidx, xidx] in fullScanCoordinates:	#we've reached a coordinate to perform a full spectrum WaRD scan
					signal_full[fullScanIdx, :], reference_full[fullScanIdx, :], _ = self._scanroutine(wavelengths = wavelengths_full, firstscan = firstscan, lastscan = lastscan)
					data_full[fullScanIdx, :] = self._baselinecorrectionroutine(wavelengths_full, signal_full[fullScanIdx, :], reference_full[fullScanIdx, :])
					delay_full[fullScanIdx] = time.time() - startTime
					x_full[fullScanIdx] = x
					y_full[fullScanIdx] = ally[yyidx]

					fullScanIdx = fullScanIdx + 1

		self.stage.moveto(x = x0, y = y0)	#go back to map center position
		self._lightOff()

		if export:
			# export as a hfile
			self._save_scanareaWaRD(
				label = label,
				x = allx, 
				y = ally, 
				delay = delay, 
				wavelengths = wavelengths, 
				reflectance = data, 
				signal = signal, 
				reference = reference,
				x_full = x_full,
				y_full = y_full,
				delay_full = delay_full,
				wavelengths_full = wavelengths_full,
				reflectance_full = data_full,
				signal_full = signal_full,
				reference_full = reference_full
				)

	def scanareaWaRD_2(self, label, wavelengths, wavelengths_full = None, xsize = 52, ysize = 52, xsteps = 27, ysteps = 27, x0 = None, y0 = None, position = None, export = True):
		x0s = [113.8, 41.4, 41.4, 113.8]	## UPDATE PROPER LOCATIONS - topright, topleft, bottomleft, bottomright
		y0s = [119.6, 119.6, 56.7, 56.7]

		# fullScanCoordinates = [		#spiral pattern to sample pts at varying distance from map center
		# 	[2,28],
		# 	[15,2],
		# 	[19,14],
		# 	[19,28],
		# 	[23,43],
		# 	[26,26],
		# 	[28,23],
		# 	[36,30],
		# 	[41,12],
		# 	[49,31]
		# ]
		fullScanCoordinates = []
		for m in range(5):
			for n in range(5):
				fullScanCoordinates.append([m*4 + 4, n*4 + 4]) #take full scans on a 5x5 grid, every 8 mm apart. Nearly centered, 8mm offset map corner

		if position is not None:
			if position < 1 or position > 4:
				print('Error: Position must hold a value from 1-4. User provided {0}. Scanning centered at current stage position'.format(position))
			else:
				x0 = x0s[position-1]
				y0 = y0s[position-1]

		currentx, currenty = self.stage.position # return position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		wavelengths = self._cleanwavelengthinput(wavelengths)
		if wavelengths_full is not None:
			wavelengths_full = self._cleanwavelengthinput(wavelengths_full)
		else:
			wavelengths_full = np.linspace(1700, 2000, 151).astype(int)

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((ysteps, xsteps, len(wavelengths)))
		signal = np.zeros((ysteps, xsteps, len(wavelengths)))
		reference = np.zeros((ysteps, xsteps, len(wavelengths)))
		delay = np.zeros((ysteps, xsteps))

		data_full = np.zeros((len(fullScanCoordinates), len(wavelengths_full)))
		signal_full = np.zeros((len(fullScanCoordinates), len(wavelengths_full)))
		reference_full = np.zeros((len(fullScanCoordinates), len(wavelengths_full)))
		delay_full = np.zeros((len(fullScanCoordinates),))
		x_full = np.zeros((len(fullScanCoordinates),))
		y_full = np.zeros((len(fullScanCoordinates),))

		fullScanIdx = 0

		firstscan = True
		lastscan = False
		reverse= -1 # for snaking
		startTime = time.time()
		for xidx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			reverse=reverse*(-1)
			for yidx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
				if xidx == xsteps-1 and yidx == ysteps-1:
					lastScan = True
				# Condition to map in a snake pattern rather than coming back to first x point
				wlThread = threading.Thread(target = self._goToWavelength, args = (wavelengths[0],))
				wlThread.start()

				if reverse > 0: #go in the forward direction
					yyidx = yidx
				else:			# go in reverse direction
					yyidx = ysteps-1-yidx

				moveThread = threading.Thread(target = self.stage.moveto, args = (x, ally[yyidx]))
				moveThread.start()
				wlThread.join()
				moveThread.join()

				signal[yyidx, xidx, :], reference[yyidx, xidx, :] = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan, flush = False)
				data[yyidx, xidx, :] = self._baselinecorrectionroutine(wavelengths, signal[yyidx, xidx, :], reference[yyidx, xidx, :])
				delay[yyidx, xidx] = time.time() - startTime #time in seconds since scan began
				firstscan = False

				if [yyidx, xidx] in fullScanCoordinates:	#we've reached a coordinate to perform a full spectrum WaRD scan
					signal_full[fullScanIdx, :], reference_full[fullScanIdx, :] = self._scanroutine(wavelengths = wavelengths_full, firstscan = firstscan, lastscan = lastscan, flush = False)
					data_full[fullScanIdx, :] = self._baselinecorrectionroutine(wavelengths_full, signal_full[fullScanIdx, :], reference_full[fullScanIdx, :])
					delay_full[fullScanIdx] = time.time() - startTime
					x_full[fullScanIdx] = x
					y_full[fullScanIdx] = ally[yyidx]

					fullScanIdx = fullScanIdx + 1

		self.stage.moveto(x = x0, y = y0)	#go back to map center position
		self._lightOff()

		if export:
			# export as a hfile
			self._save_scanareaWaRD(
				label = label,
				x = allx, 
				y = ally, 
				delay = delay, 
				wavelengths = wavelengths, 
				reflectance = data, 
				signal = signal, 
				reference = reference,
				x_full = x_full,
				y_full = y_full,
				delay_full = delay_full,
				wavelengths_full = wavelengths_full,
				reflectance_full = data_full,
				signal_full = signal_full,
				reference_full = reference_full
				)

	def scanLBIC(self, label, wavelengths, xsize, ysize, xsteps, ysteps, x0 = None, y0 = None, export = True):
		# clean up wavelengths input
		wavelengths = self._cleanwavelengthinput(wavelengths)

		currentx, currenty = self.stage.position # return position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		signal = np.zeros((ysteps, xsteps, len(wavelengths)))
		reference = np.zeros((ysteps, xsteps, len(wavelengths)))
		delay = np.zeros((ysteps, xsteps))

		firstscan = True
		lastscan = False
		reverse= -1 # for snaking
		startTime = time.time()
		for xidx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			reverse=reverse*(-1)
			for yidx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
				if xidx == xsteps-1 and yidx == ysteps-1:
					lastScan = True
				# Condition to map in a snake pattern rather than coming back to first x point
				wlThread = threading.Thread(target = self._goToWavelength, args = (wavelengths[0],))
				wlThread.start()

				if reverse > 0: #go in the forward direction
					moveThread = threading.Thread(target = self.stage.moveto, args = (x, y))
					moveThread.start()
					wlThread.join()
					moveThread.join()

					signal[yidx, xidx, :], reference[yidx, xidx, :], _ = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					delay[yidx, xidx] = time.time() - startTime #time in seconds since scan began
				else: # go in the reverse direction
					moveThread = threading.Thread(target = self.stage.moveto, args = (x, ally[ysteps-1-yidx]))
					moveThread.start()
					wlThread.join()
					moveThread.join()

					signal[ysteps-1-yidx, xidx, :], reference[ysteps-1-yidx, xidx, :], _ = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					delay[ysteps-1-yidx, xidx] = time.time() - startTime #time in seconds since scan began
				firstscan = False
		self.stage.moveto(x = x0, y = y0)	#go back to map center position
		self._lightOff()

		if export:
			# export as a hfile
			self._save_scanLBIC(
				label = label,
				x = allx, 
				y = ally, 
				delay = delay, 
				wavelengths = wavelengths, 
				signal = signal, 
				reference = reference
				)

	# internal methods
	def _scanroutine(self, wavelengths, firstscan = True, lastscan = True, flush = True):
		self._goToWavelength(wavelengths[0])
		if firstscan:
			self._lightOn()

		signal = np.zeros(wavelengths.shape)
		ref = np.zeros(wavelengths.shape)
		ratio = np.zeros(wavelengths.shape)
		for idx, wl in tqdm(enumerate(wavelengths), total = wavelengths.shape[0], desc = 'Scanning {0:.1f}-{1:.1f} nm'.format(wavelengths[0], wavelengths[-1]), leave = False):
			self.__flushcounter += 1
			if self.__flushcounter >= self.__flushinterval and flush:
				self.f.flush()
				self.__flushcounter = 0

			self._goToWavelength(wl)
			out = self.daq.read()
			signal[idx] = out['IntSphere']['Mean']
			ref[idx] = out['Reference']['Mean']
		
		if lastscan:
			self._lightOff()

		return signal, ref

	def _flyscanroutine(self, wavelength, x0, x1, numpts, firstscan = True, lastscan = True):
		def clipTime(timeraw, data, rampTime):
			tmax = max(timeraw) - rampTime
			tmin = rampTime

			return data[(timeraw>tmin) & (timeraw<tmax)]

		rampDistance = 2	#distance traveled before the stage reaches constant speed
		rampTime = 0.5		#time elapsed before the stage reaches constant speed
		useFraction = 1	    #fraction of each time step to use. Valid values = 0.1 - 1, although very small values will likely hurt data quality. 1 = use entire time step, 0.5 = only use center 50% of timestep, etc.
		# Spread out the line scan endpoints to account for acceleration runway
		if x0 > x1:
			x0 = x0 + rampDistance
			x1 = x1 - rampDistance
		else:
			x0 = x0 - rampDistance
			x1 = x1 + rampDistance

		self.stage.moveto(x = x0)	#move to flyscan start position
		if firstscan:
			self._lightOn()

		self.daq.startBG()	#start background acquisition
		self.stage.moveto(x = x1)	#move to flyscan end position
		timeraw, detectorData = self.daq.stopBG()	#stop and read data from background acquisition

		signalraw = detectorData[:,0]
		referenceraw = detectorData[:,1]

		signal = clipTime(timeraw, signalraw, rampTime)
		reference = clipTime(timeraw, referenceraw, rampTime)
		time = clipTime(timeraw, timeraw, rampTime)
		data = self._baselinecorrectionroutine(wavelength, signal, reference)
		
		time = time - time.min()	#force time to start at 0
		endtime = time.max()
		timestep = endtime / numpts
		dropTime = timestep * 0.5 * (1-useFraction)	#amount of time to drop from beginning/end of each timestep.
		reflectance = np.zeros((numpts,))

		for i in range(numpts):
			tmin = timestep*i + dropTime
			tmax = timestep*(i+1) - dropTime
			ptData = data[(time > tmin)&(time < tmax)]
			reflectance[i] = ptData.mean()
		if lastscan:
			self._lightOff()

		return reflectance, timeraw, signalraw, referenceraw

	def _baselinecorrectionroutine(self, wavelengths, signal, reference, ratio = None):
		if self.__baselineTaken == False:
			raise ValueError("Take baseline first")

		# corrected = np.zeros(wavelengths.shape)
		if self.processPulseTrain:
			# corrected = np.divide(ratio, self.__baseline['Ratio'])
			numerator = np.zeros(wavelengths.shape)
			denominator = np.zeros(wavelengths.shape)
			for idx, wl in enumerate(wavelengths):
				# meas = signal[idx]/reference[idx]
				bl_idx = np.where(self.__baseline['Wavelengths'] == wl)[0]
				numerator[idx] = (signal[idx]) / (self.__baseline['LightRaw'][bl_idx])
				denominator[idx] = (reference[idx]) / (self.__baseline['LightRefRaw'][bl_idx])
				# denominator[idx] = 1
				# corrected[idx] = (meas-self.__baseline['Dark']) / (self.__baseline['Light'][bl_idx]-self.__baseline['Dark']) 
			corrected = numerator/denominator
		else:
			numerator = np.zeros(wavelengths.shape)
			denominator = np.zeros(wavelengths.shape)
			for idx, wl in enumerate(wavelengths):
				# meas = signal[idx]/reference[idx]
				bl_idx = np.where(self.__baseline['Wavelengths'] == wl)[0]
				numerator[idx] = (signal[idx]-self.__baseline['DarkRaw']) / (self.__baseline['LightRaw'][bl_idx]-self.__baseline['DarkRaw'])
				denominator[idx] = (reference[idx]-self.__baseline['DarkRefRaw']) / (self.__baseline['LightRefRaw'][bl_idx]-self.__baseline['DarkRefRaw'])
				# denominator[idx] = 1
				# corrected[idx] = (meas-self.__baseline['Dark']) / (self.__baseline['Light'][bl_idx]-self.__baseline['Dark']) 
			corrected = numerator/denominator
		
		return corrected

	def _findedges(self, x, r, ax = None):
		### Given stage positions x and reflectance values r from a line scan at a single wavelength, compute the edges and center of 
		# the sample area using the first derivative. If given an axis handle, plots the line scan + suggested positions to this axis.
		r1 = np.gradient(r)
		# r2 = np.gradient(r1)
		
		x1 = x[np.where(r1==r1.max())]
		x2 = x[np.where(r1==r1.min())]  
		if x1 > x2:   #force x2 > x1 - initial order depends on whether reflectance is higher or lower on target area vs background
			temp = x1
			x1 = x2
			x2 = temp    
		center = np.mean([x1,x2])
		rng = x2[0]-x1[0]
		
		if ax is not None:
			ax.plot(x,r)
			ylim0 = [x for x in plt.ylim()]
			ax.plot([x1,x1], ylim0, color = 'r', linestyle = '--')
			ax.plot([x2,x2], ylim0, color = 'r', linestyle = '--')
			ax.plot([center, center], ylim0, color = 'r', linestyle = ':')
			ylim0[1] += 0.15 * (ylim0[1]-ylim0[0])
			plt.ylim(ylim0)
			ax.text(0.5, 0.98,
					'Center: {0:.3f}, Range: {1:.3f}'.format(center, rng),
					verticalalignment = 'top', 
					horizontalalignment = 'center',
					transform = ax.transAxes,
					fontsize = 16,
		#             color = 'g'
				   )
		return center, rng

	def _cleanwavelengthinput(self, wavelength):
		if wavelength is None:
			wavelength = self.__baseline['Wavelengths'] #if no wavelengths specified, assume scanning over baseline wavelengths.
		# clean up wavelengths input
		if type(wavelength) is np.ndarray:
			if wavelength.shape == ():
				wavelength = np.array([wavelength])	#cast to (1,)
			else:
				pass 	#should already be good
		elif type(wavelength) is list:
			wavelength = np.array(wavelength)
		else:
			wavelength = np.array([wavelength])	#assume we have a single int/float value here. if its a string we'll throw a normal error downstream
	
		return wavelength
	
	### Save methods to dump measurements to hdf5 file. Currently copied from PL code, need to fit this to the mapping data.
	def _getsavepath(self, label):
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputdir = os.path.join(root, datafolder, todaysDate)	#set outputdir folder so the scan saves on correct date (date of scan completion)

		### figure out the sample directory, name, total filepath
		if not os.path.exists(self.outputdir):
			os.mkdir(self.outputdir)
		fids = os.listdir(self.outputdir)

		fileNumber = 1
		for fid in fids:
			if 'frgmapper' in fid:
				fileNumber = fileNumber + 1

		if label is not None:
			fname = 'frgmapper_{0:04d}_{1}.h5'.format(fileNumber, label)
		else:
			fname = 'frgmapper_{0:04d}.h5'.format(fileNumber)
		fpath = os.path.join(self.outputdir, fname)


		

		return fpath

	def _save_generic(self, f, label, scantype):
		### General information that will be saved regardless of which method (point scan, area scan, etc.) was used. Should be called
		# at the beginning of any scan.

		# sample info
		info = f.create_group('/info')
		info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
		
		temp = info.create_dataset('name', data = label.encode('utf-8'))
		temp.attrs['description'] = 'Sample name.'

		date = info.create_dataset('date', data = datetime.datetime.now().strftime('%Y-%m-%d').encode('utf-8'))
		temp.attrs['description'] = 'Measurement start date.'
		
		temp = info.create_dataset('time', data =  datetime.datetime.now().strftime('%H:%M:%S').encode('utf-8'))
		temp.attrs['description'] = 'Measurement start time of day.'

		temp = info.create_dataset('completed', data =  0)
		temp.attrs['description'] = 'Boolean flag, true if measurement was successfully completed. If false, portion of data is likely missing, and should be reported as NaNs'

		temp = info.create_dataset('type', data = scantype.encode('utf-8'))
		temp.attrs['description'] = 'Type of measurement held in this file.'

		# measurement settings
		settings = f.create_group('/settings')
		settings.attrs['description'] = 'Settings used for measurements.'

		temp = settings.create_dataset('hardware', data = self.__hardwareSetup.encode('utf-8'))
		temp.attrs['description'] = 'Light source/ardware used for this scan - either the newport lamp + monochromator, or nkt compact + select'

		temp = settings.create_dataset('dwelltime', data = self.__dwelltime)
		temp.attrs['description'] = 'Time spent collecting signal at each wavelength.'

		temp = settings.create_dataset('count_rate', data = self.daq.rate)
		temp.attrs['description'] = 'Acquisition rate (Hz) of data acquisition unit when reading detector voltages.'

		temp = settings.create_dataset('num_counts', data = self.daq.counts)
		temp.attrs['description'] = 'Voltage counts per detector used to quantify reflectance values.'

		temp = settings.create_dataset('position', data = np.array(self.stage.position))
		temp.attrs['description'] = 'Stage position (x,y) during scan.'

		completed = settings.create_dataset('scan_completed', data = 0)
		completed.attrs['description'] = 'Flag indicating whether scan was run to completion. 0 if cancelled/interrupted.'

		# baseline measurement
		baseline = f.create_group('/settings/baseline')

		temp = baseline.create_dataset('wavelengths', data = np.array(self.__baseline['Wavelengths']))
		temp.attrs['description'] = 'Wavelengths (nm) scanned for baseline measurement'

		temp = baseline.create_dataset('sphere_ill', data = np.array(self.__baseline['LightRaw']))
		temp.attrs['description'] = 'Raw counts for integrating sphere detector during illuminated baseline measurement'

		temp = baseline.create_dataset('ref_ill', data = np.array(self.__baseline['LightRefRaw']))
		temp.attrs['description'] = 'Raw counts for reference detector during illuminated baseline measurement'

		temp = baseline.create_dataset('ratio_ill', data = np.array(self.__baseline['Light']))
		temp.attrs['description'] = 'Ratio of sphere/reference counts during illuminated baseline measurement. This number is considered 100\% reflectance'

		temp = baseline.create_dataset('sphere_dark', data = np.array(self.__baseline['DarkRaw']))
		temp.attrs['description'] = 'Raw counts for integrating sphere detector during dark baseline measurement. Single point, independent of wavelength.'

		temp = baseline.create_dataset('ref_dark', data = np.array(self.__baseline['DarkRefRaw']))
		temp.attrs['description'] = 'Raw counts for reference detector during dark baseline measurement. Single point, independent of wavelength.'

		temp = baseline.create_dataset('ratio_dark', data = np.array(self.__baseline['Dark']))
		temp.attrs['description'] = 'Ratio of sphere/reference counts during illuminated baseline measurement. This number is considered 0\% reflectance. Single point, independent of wavelength.'

		return info, settings, baseline, completed

	def _save_scanareaWaRD(self, label, x, y, delay, wavelengths, reflectance, signal, reference, x_full, y_full, delay_full, wavelengths_full, reflectance_full, signal_full, reference_full):
		
		fpath = self._getsavepath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as self.f:
			
			info, settings, baseline, completed = self._save_generic(f = self.f, label = label, scantype = 'scanareaWaRD')

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('numfull', data = np.array(len(x_full)))
			temp.attrs['description'] = 'Number of points at which a full WaRD spectrum was acquired'			

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0 '			

			## measured data 
			rawdata = self.f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			## measured data, full WaRD spectra
			temp = rawdata.create_dataset('x_full', data = np.array(x_full))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y_full', data = np.array(y_full))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx_full', data = np.array(x_full - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely_full', data = np.array(y_full - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths_full', data = np.array(wavelengths_full))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance_full', data = np.array(reflectance_full))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('signalRaw_full', data = np.array(signal_full))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw_full', data = np.array(reference_full))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay_full', data = np.array(delay_full))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			completed = 1
		print('Data saved to {0}'.format(fpath))		

	def _save_flyscanarea(self, label, x, y, delay, wavelengths, reflectance):
		
		fpath = self._getsavepath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings, baseline = self._save_generic(f, label = label)

			## add scan type to info
			temp = info.create_dataset('type', data = 'flyscanarea'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'		

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0. Note that steps in x are divided out of a continuous line scan.'			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point. Note that points in x are divided out of a continous line scan.'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point. Note that points in x are divided out of a continous line scan.'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) at which sequential flyscan maps were performed.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each line scan was acquired at. [wl, y]. Measured as seconds since first line scan.'			

		print('Data saved to {0}'.format(fpath))

	def _save_timeseries(self, label, wavelengths, reflectance, delay, duration, interval, signal, reference, logtemperature, temperature):

		fpath = self._getsavepath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings, baseline = self._save_generic(f, label = label)		

			## add scan type to info
			temp = info.create_dataset('type', data = 'timeseries'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'

			## add scan parameters to settings
			temp = settings.create_dataset('duration', data = np.array(duration))
			temp.attrs['description'] = 'Total time (s) desired for time series.'			

			temp = settings.create_dataset('interval', data = np.array(interval))
			temp.attrs['description'] = 'Time (s) desired between subsequent scans.'

			if logtemperature:
				temp = settings.create_dataset('temperatureLogged', data = 1)
			else:
				temp = settings.create_dataset('temperatureLogged', data = 0)
			temp.attrs['description'] = 'Temperature logged during measurements. Note that this is the temperature of the heating pad in slot 2, actual sample temperature may vary.'

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'
			
			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'
			
			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			temp = rawdata.create_dataset('temperature', data = np.array(temperature))
			temp.attrs['description'] = 'Temperature (C) of heating pad in slot 2 at the time that each scan was acquired at.'

		print('Data saved to {0}'.format(fpath))

	def _save_scanLBIC(self, label, x, y, delay, wavelengths, signal, reference):
		fpath = self._getsavepath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings = self._save_generic(f, label = label, include_baseline = False)

			## add scan type to info
			temp = info.create_dataset('type', data = 'scanLBIC'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'		

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanarea()), leave stepsize as 0 '			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for calculating LBIC current. (V across 50 ohm terminating resistor)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

		print('Data saved to {0}'.format(fpath))	

	# def _save_findArea(self, label, wavelength, reflectance):

	def _save_scanArea(self, label, x, y, delay, wavelengths, reflectance, signal, reference):
		
		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings, baseline = self._saveGeneralInformation(f, label = label)

			## add scan type to info
			temp = info.create_dataset('type', data = 'scanArea'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'		

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0 '			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

		print('Data saved to {0}'.format(fpath))		

	def _save_scanAreaWaRD(self, label, x, y, delay, wavelengths, reflectance, signal, reference, x_full, y_full, delay_full, wavelengths_full, reflectance_full, signal_full, reference_full):
		
		fpath = self._getsavepath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings, baseline = self._save_generic(f, label = label, scantype = 'scanareaWaRD')

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('numfull', data = np.array(len(x_full)))
			temp.attrs['description'] = 'Number of points at which a full WaRD spectrum was acquired'			

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0 '			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			## measured data, full WaRD spectra
			temp = rawdata.create_dataset('x_full', data = np.array(x_full))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y_full', data = np.array(y_full))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx_full', data = np.array(x_full - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely_full', data = np.array(y_full - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths_full', data = np.array(wavelengths_full))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance_full', data = np.array(reflectance_full))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('signalRaw_full', data = np.array(signal_full))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw_full', data = np.array(reference_full))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay_full', data = np.array(delay_full))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

		print('Data saved to {0}'.format(fpath))		

	def _save_flyscanArea(self, label, x, y, delay, wavelengths, reflectance):
		
		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings, baseline = self._saveGeneralInformation(f, label = label)

			## add scan type to info
			temp = info.create_dataset('type', data = 'flyscanArea'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'		

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0. Note that steps in x are divided out of a continuous line scan.'			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point. Note that points in x are divided out of a continous line scan.'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point. Note that points in x are divided out of a continous line scan.'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) at which sequential flyscan maps were performed.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each line scan was acquired at. [wl, y]. Measured as seconds since first line scan.'			

		print('Data saved to {0}'.format(fpath))

	def _save_timeSeries(self, label, wavelengths, reflectance, delay, duration, interval, signal, reference, logtemperature, temperature):

		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings, baseline = self._saveGeneralInformation(f, label = label)		

			## add scan type to info
			temp = info.create_dataset('type', data = 'timeSeries'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'

			## add scan parameters to settings
			temp = settings.create_dataset('duration', data = np.array(duration))
			temp.attrs['description'] = 'Total time (s) desired for time series.'			

			temp = settings.create_dataset('interval', data = np.array(interval))
			temp.attrs['description'] = 'Time (s) desired between subsequent scans.'

			if logtemperature:
				temp = settings.create_dataset('temperatureLogged', data = 1)
			else:
				temp = settings.create_dataset('temperatureLogged', data = 0)
			temp.attrs['description'] = 'Temperature logged during measurements. Note that this is the temperature of the heating pad in slot 2, actual sample temperature may vary.'

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'
			
			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for integrating sphere detector. (V)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'
			
			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

			temp = rawdata.create_dataset('temperature', data = np.array(temperature))
			temp.attrs['description'] = 'Temperature (C) of heating pad in slot 2 at the time that each scan was acquired at.'

		print('Data saved to {0}'.format(fpath))

	def _save_scanLBIC(self, label, x, y, delay, wavelengths, signal, reference):
		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w', swmr = True, libver = 'latest') as f:
			
			info, settings = self._saveGeneralInformation(f, label = label, include_baseline = False)

			## add scan type to info
			temp = info.create_dataset('type', data = 'scanLBIC'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'		

			## add scan parameters to settings
			temp = settings.create_dataset('numx', data = np.array(x.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in x'			

			temp = settings.create_dataset('numy', data = np.array(y.shape[0]))
			temp.attrs['description'] = 'Number of points scanned in y'

			temp = settings.create_dataset('rangex', data = np.array(np.abs(x[-1] - x[0])))
			temp.attrs['description'] = 'Range scanned in x (mm)'

			temp = settings.create_dataset('rangey', data = np.array(np.abs(y[-1] - y[0])))
			temp.attrs['description'] = 'Range scanned in y (mm)'

			# calculate step size. Calculates the average step size in x and y. If either axis has length 1 (ie line scan), only consider step size
			# in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0
			countedaxes = 0
			stepsize = 0
			if x.shape[0] > 1:
				stepsize = stepsize + np.abs(x[1] - x[0])
				countedaxes = countedaxes + 1
			if y.shape[0] > 1:
				stepsize = stepsize + np.abs(y[1] - y[0])
				countedaxes = countedaxes + 1
			if countedaxes:
				stepsize = stepsize / countedaxes

			temp = settings.create_dataset('stepsize', data = np.array(stepsize))
			temp.attrs['description'] = 'Average step size (mm) in x and y. If either axis has length 1 (ie line scan), only consider step size in the other axis. If both axes have length 0 (point scan, although not a realistic outcome for .scanArea()), leave stepsize as 0 '			

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('x', data = np.array(x))
			temp.attrs['description'] = 'Absolute X coordinate (mm) per point'

			temp = rawdata.create_dataset('y', data = np.array(y))
			temp.attrs['description'] = 'Absolute Y coordinate (mm) per point'

			temp = rawdata.create_dataset('relx', data = np.array(x - np.min(x)))
			temp.attrs['description'] = 'Relative X coordinate (mm) per point'

			temp = rawdata.create_dataset('rely', data = np.array(y - np.min(y)))
			temp.attrs['description'] = 'Relative Y coordinate (mm) per point'						

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('signalRaw', data = np.array(signal))
			temp.attrs['description'] = 'Raw signal for calculating LBIC current. (V across 50 ohm terminating resistor)'

			temp = rawdata.create_dataset('referenceRaw', data = np.array(reference))
			temp.attrs['description'] = 'Raw signal for reference detector. (V)'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

		print('Data saved to {0}'.format(fpath))	


class controlMono(controlGeneric):

	def __init__(self, dwelltime = 0.25):
		super().__init__(dwelltime = dwelltime)
		self.__hardwareSetup = 'mono'		#distinguish whether saved data comes from the mono or nkt setup
		self.stage = None
		self.mono = None
		self.daq = None
		self.connect()
		self.daq.useExtClock = False	#dont use external trigger to drive daq
		self.processPulseTrain = False
		plt.ion()	#make plots of results non-blocking

	def connect(self):
		#connect to mono, stage, detector+daq hardware
		self.mono = Mono()
		print("mono connected")

		self.daq = DAQ(dwelltime = self.dwelltime)
		print("daq connected")

		self.stage = Thorlabs_LTS150_xy()
		print("stage connected")

	def disconnect(self):
		self.mono.disconnect()
		self.daq.disconnect()
		self.stage.disable()
		
	### internal methods specific to mono hardware setup

	def _goToWavelength(self, wavelength):
		self.mono.wavelength = wavelength

	def _lightOn(self):
		if not self.mono.shutterOpenStatus:
			self.mono.open_shutter()
		return True

	def _lightOff(self):
		if self.mono.shutterOpenStatus:
			self.mono.close_shutter()
		return True

class controlNKT(controlGeneric):

	def __init__(self, dwelltime = 0.2):
		super().__init__(dwelltime = dwelltime)
		self.__hardwareSetup = 'nkt'		#distinguish whether saved data comes from the mono or nkt setup
		self.stage = None
		self.select = None
		self.compact = None
		self.daq = None
		self.heater = None
		self.lia = None #SR830 lock-in amplifier
		self.connect()
		self.daq.useExtClock = False	#use external Compact trigger to drive daq, match the laser pulse train
		self.processPulseTrain = False
		plt.ion()	#make plots of results non-blocking

	def connect(self):
		#connect to mono, stage, detector+daq hardware
		self.lia = SR830('GPIB0::8::INSTR')
		print("SR830 LIA connected")
		self.__set_up_lia()

		self.compact = Compact(
			port = 'COM16',
			pulseFrequency = 21505
			)
		print("compact connected")

		self.select = Select(
			port = 'COM16'
			)
		self.select.selectAOTF('ir')
		self.select.setAOTF(1700, 0.6)
		print("select+rf driver connected")

		self.daq = DAQ(
			dwelltime = self.dwelltime,
			rate = 50000,
			countsPerTrigger = 3,
			countsPulseDuration = 20
			)
		print("daq connected")

		self.stage = Thorlabs_LTS150_xy()
		print("stage connected")

		self.heater = Omega(
			port = 'COM15'
			)
		print("heater connected")

	def disconnect(self):
		self.compact.disconnect()
		self.select.disconnect()
		self.daq.disconnect()
		self.stage.disable()
		self.heater.disconnect()

	def __set_up_lia(self):
		#https://www.thinksrs.com/downloads/pdfs/manuals/SR830m.pdf
		input('Ensure that orange taped "mapper" cables are attached to the appropriate inputs on the SR830 Lock-In Amplifier under the optical table - press Enter to confirm')
		self.lia.channel1 = 'R'
		self.lia.filter_slope = 24
		self.lia.input_config = 'A'
		self.lia.input_coupling = 'DC'
		self.lia.input_grounding = 'Float'
		self.lia.input_notch_config = 'Both'
		self.lia.sensitivity = 0.02 #2x10 mV
		# self.lia.set_scaling('R',0, 1.0)
		self.lia.write('OEXP 3,0.0,0') #turn output expansion off.
		self.lia.time_constant = .001 #1x1 ms
		self.lia.reference_source = 'External'

		return True


	### internal methods specific to nkt hardware setup

	def _goToWavelength(self, wavelength):
		if not self.select.rfOn:	#make sure the rf driver is on
			self.select.on()
		self.select.setSingleAOTF(wavelength)
		return True

	def _lightOn(self):
		self.preCheck()	#checks shutters and interlock, gives user a chance to remedy before continuing
		# if not self.compact.emissionOn:
		self.compact.on()
		return True
		
	def _lightOff(self):
		self.compact.off()
		return True

	def preCheck(self):
		goodToGo = False
		self.compact.resetInterlock()  # this will "press the reset button on the front panel". interlock will stay unsatisfied if door is open.
		while not goodToGo:
			if self.select.checkShutter() and self.compact.checkInterlock():
				goodToGo = True
			else:
				input('Press Enter when issues have been resolved')

		return goodToGo