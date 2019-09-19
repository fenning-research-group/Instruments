import numpy as np
import matplotlib.pyplot as plt
import os
import serial
import time
import json
import datetime
from .stage import stage
from .mono import mono
from .daq import daq
import datetime
from tqdm import tqdm
import h5py
import threading

root = 'C:\\Users\\PVGroup\\Desktop\\frgmapper'
if not os.path.exists(root):
	os.mkdir(root)
datafolder = os.path.join(root, 'Data')
if not os.path.exists(datafolder):
	os.mkdir(datafolder)

class controlGeneric(object):
	def __init__(self, dwelltime = 0.1):
		todaysDate = datetime.datetime.now().strftime('%Y%m%d')
		self.outputdir = os.path.join(root, datafolder, todaysDate)
		self.__hardwareSetup = 'mono'		#distinguish whether saved data comes from the mono or nkt setup
		self.__dwelltime = dwelltime
		self.__baselineTaken = False
		self.__baseline = {}
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
	def generateWavelengths(self, wmin = 1700, wmax = 2000, wsteps = 151):
		wavelengths = np.linspace(wmin, wmax, wsteps)
		return wavelengths

	def takeBaseline(self, wavelengths):
		# clean up wavelengths input
		wavelengths = np.array(wavelengths)

		#light baseline
		self.__baseline['Wavelengths'] = wavelengths
		self.__baseline['LightRaw'], self.__baseline['LightRefRaw'] = self._scanroutine(wavelengths)
		self.__baseline['Light'] = np.divide(self.__baseline['LightRaw'], self.__baseline['LightRefRaw'])
		
		#dark baseline
		storeddwelltime = self.__dwelltime
		self.dwelltime = 5	#take a long acquisition for the dark baseline, as it is a single point measurement
		out = self.daq.read()
		self.dwelltime = storeddwelltime
		
		self.__baseline['DarkRaw'] = out['IntSphere']['Mean']
		self.__baseline['DarkRefRaw'] = out['Reference']['Mean']
		self.__baseline['Dark'] = self.__baseline['DarkRaw'] / self.__baseline['DarkRefRaw']
		
		self.__baselineTaken = True

	def scanPoint(self, label, wavelengths, plot = True, export = True):
		# clean up wavelengths input
		wavelengths = self._cleanWavelengthInput(wavelengths)

		signal, reference = self._scanroutine(wavelengths)
		reflectance = self._baselineCorrectionRoutine(wavelengths, signal, reference)

		data = {
			'Label': label,
			'Wavelengths': wavelengths.tolist(),
			'Reflectance': reflectance.tolist(),
		}

		# if verbose:
			### TODO: All nested numpy arrays need to be converted to lists to be compatible with json dumps. Commenting this out til hdf5, wont be an issue then
			# data['Verbose'] = {
			# 	'Signal': signal.tolist(),
			# 	'Reference': reference.tolist(),
			# 	'Baseline': self.__baseline.tolist()
			# }

		if export and self.outputdir is not None:
			# self._saveTakeScan(label = label, wavelengths = wavelengths, reflectance = reflectance)
			# fpath = os.path.join(self.outputdir, label + '.json')
			# with open(fpath, 'w') as f:
			# 	json.dump(data, f)
			self._save_scanPoint(label = label, wavelengths = wavelengths, reflectance = reflectance)

		if plot:
			plt.plot(data['Wavelengths'],data['Reflectance'])
			plt.xlabel('Wavelength (nm)')
			plt.ylabel('Reflectance')
			plt.title(label)
			plt.show()

	def findArea(self, wavelength, xsize = 30, ysize = 30, xsteps = 40, ysteps = 40, plot = True, export = False):
		### method to find sample edges. does two line scans in a cross over the sample at a single wavelength.
		# clean up wavelengths input
		wavelength = self._cleanWavelengthInput(wavelength)

		if wavelength.shape[0] > 1:
			print('Please use a single wavelength for findArea - aborting')
			return False
		
		# self.stage.gotocenter() #go to center position, where sample is centered on integrating sphere port. Might need to remove this line later if inconvenient
		x0, y0 = self.stage.position

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)
		

		self._goToWavelength(wavelength[0])
		
		self.stage.moveto(x = allx[0], y = y0)
		self._lightOn()		
		xdata = np.zeros((xsteps,))
		for idx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			self.stage.moveto(x = x)
			out = self.daq.read()
			signal = [out['IntSphere']['Mean']]
			ref = [out['Reference']['Mean']]
			xdata[idx] = self._baselineCorrectionRoutine(wavelengths = wavelength, signal = signal, reference = ref)
		self._lightOff()

		self.stage.moveto(x = x0, y = ally[0])
		self._lightOn()
		ydata = np.zeros((ysteps,))
		for idx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
			self.stage.moveto(y = y)
			out = self.daq.read()
			signal = [out['IntSphere']['Mean']]
			ref = [out['Reference']['Mean']]
			ydata[idx]= self._baselineCorrectionRoutine(wavelengths = wavelength, signal = signal, reference = ref)
		self._lightOff()
		self.stage.moveto(x = x0, y = y0) #return to original position

		# if export:
			# self._save_findArea(x = allx, y = ally, wavelength = wavelength, reflectance_x = xdata, reflectance_y = ydata)

		if plot:
			fig, ax = plt.subplots(2,1)
			ax[0].plot(allx, xdata)
			ax[0].set_xlabel('X Position (mm)')
			ax[0].set_ylabel('Reflectance at {0:d} nm'.format(wavelength[0]))
			ax[0].set_title('X Scan')

			ax[1].plot(ally, ydata)
			ax[1].set_xlabel('Y Position (mm)')
			ax[1].set_ylabel('Reflectance at {0:d} nm'.format(wavelength[0]))
			ax[1].set_title('Y Scan')
			plt.tight_layout()
			plt.show()
		# return the centroid, width/bounds if found
		
		# HERE add code to find sample area based on the variation of reflectance

	def scanArea(self, label, wavelengths, xsize, ysize, xsteps = 21, ysteps = 21, x0 = None, y0 = None, export = True):
		# clean up wavelengths input
		wavelengths = self._cleanWavelengthInput(wavelengths)

		currentx, currenty = self.stage.position # return position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((ysteps, xsteps, len(wavelengths)))
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

					signal, reference = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					data[yidx, xidx, :] = self._baselineCorrectionRoutine(wavelengths, signal, reference)
					delay[yidx, xidx] = time.time() - startTime #time in seconds since scan began
				else: # go in the reverse direction
					moveThread = threading.Thread(target = self.stage.moveto, args = (x, ally[ysteps-1-yidx]))
					moveThread.start()
					wlThread.join()
					moveThread.join()

					signal,reference = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					data[ysteps-1-yidx, xidx, :]= self._baselineCorrectionRoutine(wavelengths, signal, reference) # baseline correction
					delay[ysteps-1-yidx, xidx] = time.time() - startTime #time in seconds since scan began
				firstscan = False
		self.stage.moveto(x = x0, y = y0)	#go back to map center position

		if export:
			# export as a hfile
			self._save_scanArea(label = label, x = allx, y = ally, delay = delay, wavelengths = wavelengths, reflectance = data)

	def flyscanArea(self, label, wavelengths, xsize, ysize, xsteps = 21, ysteps = 21, x0 = None, y0 = None, export = True):
		# clean up wavelengths input
		wavelengths = self._cleanWavelengthInput(wavelengths)

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
			self._save_flyscanArea(label = label, 
				x = allx, 
				y = ally, 
				delay = delay, 
				wavelengths = wavelengths, 
				reflectance = data
				)

	def timeSeries(self, label, wavelengths, duration, interval, export = True):
		### records a reflectance spectrum for a given duration (seconds) at set intervals (seconds)
		#	TODO: I don't think this will work for single wavelength inputs

		# clean up wavelengths input

		wavelengths = np.array(wavelengths)

		reflectance = []
		delay = []
		startTime = time.time()
		pbarPercent = 0
		with tqdm(total = 100, desc = 'Scanning every {0} s for {1} s'.format(interval, duration), leave = False) as pbar:
			while (time.time() - startTime) <= duration:
				if (time.time()-startTime) >= (interval*len(delay)):	#time for the next scan
					delay.append(time.time() - startTime)
					signal, reference = self._scanroutine(wavelengths, lastscan = False)
					reflectance.append(self._baselineCorrectionRoutine(wavelengths, signal, reference))
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
		
		self._lightOff()

		reflectance = np.array(reflectance)
		delay = np.array(delay)
		if export:
			self._save_timeSeries(label = label, wavelengths = wavelengths, reflectance = reflectance, delay = delay, duration = duration, interval = interval)

		# if plot:
		# 	plt.plot(data['Wavelengths'],data['Reflectance'])
		# 	plt.xlabel('Wavelength (nm)')
		# 	plt.ylabel('Reflectance')
		# 	plt.title(label)
		# 	plt.show()
	

	# internal methods
	def _scanroutine(self, wavelengths, firstscan = True, lastscan = True):
		self._goToWavelength(wavelengths[0])
		if firstscan:
			self._lightOn()

		signal = np.zeros(wavelengths.shape)
		ref = np.zeros(wavelengths.shape)
		for idx, wl in tqdm(enumerate(wavelengths), total = wavelengths.shape[0], desc = 'Scanning {0:.1f}-{1:.1f} nm'.format(wavelengths[0], wavelengths[-1]), leave = False):
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
		data = self._baselineCorrectionRoutine(wavelength, signal, reference)
		
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

	def _baselineCorrectionRoutine(self, wavelengths, signal, reference):
		if self.__baselineTaken == False:
			raise ValueError("Take baseline first")

		corrected = np.zeros(wavelengths.shape)
		for idx, wl in enumerate(wavelengths):
			meas = signal[idx]/reference[idx]
			bl_idx = np.where(self.__baseline['Wavelengths'] == wl)[0]
			corrected[idx] = (meas-self.__baseline['Dark']) / (self.__baseline['Light'][bl_idx]-self.__baseline['Dark']) 

		return corrected

	def _cleanWavelengthInput(self, wavelength):
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
	def _getSavePath(self, label):
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

	def _saveGeneralInformation(self, f, label):
		### General information that will be saved regardless of which method (point scan, area scan, etc.) was used. Should be called
		# at the beginning of any method-specific save method.

			# sample info
			info = f.create_group('/info')
			info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
			temp = info.create_dataset('name', data = label.encode('utf-8'))
			temp.attrs['description'] = 'Sample name.'

			date = info.create_dataset('date', data = datetime.datetime.now().strftime('%Y-%m-%d').encode('utf-8'))
			temp.attrs['description'] = 'Measurement date.'
			
			temp = info.create_dataset('time', data =  datetime.datetime.now().strftime('%H:%M:%S').encode('utf-8'))
			temp.attrs['description'] = 'Measurement time of day.'

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

			return info, settings, baseline

	def _save_scanPoint(self, label, wavelengths, reflectance):
		
		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w') as f:
			
			info, settings, baseline = self._saveGeneralInformation(f, label = label)	

			## add scan type to info
			temp = info.create_dataset('type', data = 'scanPoint'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'	
			
			# raw data
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during point scan.'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as fraction (0-1), not percent!'

		print('Data saved to {0}'.format(fpath))	

	# def _save_findArea(self, label, wavelength, reflectance):

	def _save_scanArea(self, label, x, y, delay, wavelengths, reflectance):
		
		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w') as f:
			
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

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

		print('Data saved to {0}'.format(fpath))		

	def _save_flyscanArea(self, label, x, y, delay, wavelengths, reflectance):
		
		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w') as f:
			
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

	def _save_timeSeries(self, label, wavelengths, reflectance, delay, duration, interval):

		fpath = self._getSavePath(label = label)	#generate filepath for saving data

		with h5py.File(fpath, 'w') as f:
			
			info, settings, baseline = self._saveGeneralInformation(f, label = label)		

			## add scan type to info
			temp = info.create_dataset('type', data = 'timeSeries'.encode('utf-8'))
			temp.attrs['description'] = 'Type of measurement held in this file.'

			## add scan parameters to settings
			temp = settings.create_dataset('duration', data = np.array(duration))
			temp.attrs['description'] = 'Total time (s) desired for time series.'			

			temp = settings.create_dataset('interval', data = np.array(interval))
			temp.attrs['description'] = 'Time (s) desired between subsequent scans.'

			## measured data 
			rawdata = f.create_group('/data')
			rawdata.attrs['description'] = 'Data acquired during area scan.'

			temp = rawdata.create_dataset('wavelengths', data = np.array(wavelengths))
			temp.attrs['description'] = 'Wavelengths (nm) scanned per point.'

			temp = rawdata.create_dataset('reflectance', data = np.array(reflectance))
			temp.attrs['description'] = 'Baseline-corrected reflectance measured. Stored as [y, x, wl]. Stored as fraction (0-1), not percent!'

			temp = rawdata.create_dataset('delay', data = np.array(delay))
			temp.attrs['description'] = 'Time (seconds) that each scan was acquired at. Measured as seconds since first scan point.'			

		print('Data saved to {0}'.format(fpath))

	
	### Test Methods: should remove these and make a wrapper function to execute these commands instead of building it into the class
	#
	#	This method has been saved under /tests/scanStageModule as an example test. Only thing we need to do is install the frgmapper package
	#	instead of calling the filepath directly. Can be done by moving to the WaRD Mapping directory and running pip install -e frgmapper. The
	# 	-e flag (editable) makes future changes reflected in the module, so we can use import frmapper / reload(frgmapper) from anywhe (including
	#	within the test script)

	def measspectra(self):
		wave=np.linspace(1700,2000,151,dtype=int)
		wave=wave.tolist()
		self.connect()
		self.takeBaseline(wave)
		input('Place stage on integrating sphere: press enter to scan')
		self.takeScan("test",wave,True,False,False) # green stage
		input('Place mini module on sphere: press enter to scan')
		self.takeScan("test",wave,True,False,False) # minimodule

class controlMono(controlGeneric):

	def __init__(self, dwelltime = 0.1):
		super().__init__(dwelltime = dwelltime)
		self.__hardwareSetup = 'mono'		#distinguish whether saved data comes from the mono or nkt setup
		self.stage = None
		self.mono = None
		self.daq = None
		self.connect()
		plt.ion()	#make plots of results non-blocking

	def connect(self):
		#connect to mono, stage, detector+daq hardware
		self.mono = mono()
		print("mono connected")

		self.daq = daq(dwelltime = self.dwelltime)
		print("daq connected")

		self.stage = stage()
		print("stage connected")

	### internal methods specific to mono hardware setup

	def _goToWavelength(self, wavelength):
		self.mono.goToWavelength(wavelength)

	def _lightOn(self):
		if not self.mono.shutterOpenStatus:
			self.mono.openShutter()
		return True

	def _lightOff(self):
		if self.mono.shutterOpenStatus:
			self.mono.closeShutter()
		return True

class controlNKT(controlGeneric):

	def __init__(self, dwelltime = 0.1):
		super().__init__(dwelltime = dwelltime)
		self.__hardwareSetup = 'nkt'		#distinguish whether saved data comes from the mono or nkt setup
		self.stage = None
		self.select = None
		self.compact = None
		self.daq = None
		self.connect()
		plt.ion()	#make plots of results non-blocking

	def connect(self):
		#connect to mono, stage, detector+daq hardware
		self.compact = compact()
		print("compact connected")

		self.select = select()
		print("select+rf driver connected")

		self.daq = daq(dwelltime = self.dwelltime)
		print("daq connected")

		self.stage = stage()
		print("stage connected")

	### internal methods specific to nkt hardware setup

	def _goToWavelength(self, wavelength):
		if not self.select.rfOn:	#make sure the rf driver is on
			self.select.on()
		self.select.setAOTF(wavelength)
		return True

	def _lightOn(self):
		if not self.compact.emissionOn:
			self.compact.on()
		return True

	def _lightOff(self):
		if self.compact.emissionOn:
			self.compact.off()
		return True

