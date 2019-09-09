import numpy as np
import matplotlib.pyplot as plt
import os
import serial
import time
import json
from .stage import stage
from .mono import mono
from .daq import daq
import datetime
from tqdm import tqdm

class control(object):
	def __init__(self, outputdir = None, dwelltime = 0.1):
		self.outputdir = outputdir
		self.__dwelltime = dwelltime
		self.__baselineTaken = False
		self.__baseline = {}
		self._stage = None
		self._mono = None
		self._daq = None

	@property
	def dwelltime(self):
		return self.__dwelltime

	@dwelltime.setter
	def dwelltime(self, x):
		# sets daq counts to match desired measurement time (x, in seconds)
		self._daq.dwelltime = x
		self.__dwelltime = x

	def connect(self):
		#connect to spectrometer hardware
		self._mono = mono()
		self._daq = daq(dwelltime = self.dwelltime)
		print("mono connected")
		print("daq connected")

	def connectStage(self):
		#connect to stage hardware
		self._stage = stage()
		print("stage connected")

	def takeBaseline(self, wavelengths):
		# clean up wavelengths input
		wavelengths = np.array(wavelengths)

		#light baseline
		self.__baseline['Wavelengths'] = wavelengths
		self.__baseline['LightRaw'], self.__baseline['LightRefRaw'] = self._scanroutine(wavelengths)
		self.__baseline['Light'] = np.divide(self.__baseline['LightRaw'], self.__baseline['LightRefRaw'])
		
		#dark baseline
		out = self._daq.read()
		self.__baseline['DarkRaw'] = out['IntSphere']['Mean']
		self.__baseline['DarkRefRaw'] = out['Reference']['Mean']
		self.__baseline['Dark'] = self.__baseline['DarkRaw'] / self.__baseline['DarkRefRaw']
		
		self.__baselineTaken = True

	def takeScan(self, label, wavelengths, plot = False, export = True, verbose = False):
		# clean up wavelengths input
		wavelengths = np.array(wavelengths)

		signal, reference = self._scanroutine(wavelengths)
		reflectance = self._baselineCorrectionRoutine(wavelengths, signal, reference)

		data = {
			'Label': label,
			'Date': datetime.date.today().strftime('%Y/%m/%d'),
			'Time': datetime.datetime.now().strftime('%H:%M:%S'),
			'Wavelengths': wavelengths.tolist(),
			'Reflectance': reflectance.tolist(),
			'DwellTime': self.dwelltime
		}

		if verbose:
			data['Verbose'] = {
				'Signal': signal.tolist(),
				'Reference': reference.tolist(),
				'Baseline': self.__baseline.tolist()
			}

		if export and self.outputdir is not None:
			fpath = os.path.join(self.outputdir, label + '.json')
			with open(fpath, 'w') as f:
				json.dump(data, f)

		if plot:
			plt.plot(data['Wavelengths'],data['Reflectance'])
			plt.xlabel('Wavelength (nm)')
			plt.ylabel('Reflectance')
			plt.title(label)
			plt.show()

	def findArea(self, wavelength, xsize = 30, ysize = 30, xsteps = 6, ysteps = 6, plot = True, export = False):
		### method to find sample edges. does two line scans in a cross over the sample at a single wavelength.
		# clean up wavelengths input
		wavelengths = np.array(wavelength)

		if self._stage is None:
			self.connectStage() # connect stage
			self._stage.gohome()
		if self._daq is None:
			self.connect() # connect mono and daq
		
		self._stage.gotocenter() #go to center position, where sample is centered on integrating sphere port. Might need to remove this line later if inconvenient
		x0, y0 = self._stage.position

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)
		

		self._mono.goToWavelength(wavelength[0])
		
		self._stage.moveto(x = allx[0], y = y0)
		self._mono.openShutter()		
		xdata = np.zeros((xsteps, ))
		for idx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			self._stage.moveto(x = x)
			out = self._daq.read()
			intsignal = out['IntSphere']['Mean']
			ref = out['Reference']['Mean']
			xdata[idx] = self._baselineCorrectionRoutine(wavelengths = wavelength, signal = intsignal, reference = ref)
		self._mono.closeShutter()

		self._stage.moveto(x = x0, y = ally[0])
		self._mono.openShutter()
		ydata = np.zeros((xsteps, ))
		for idx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
			self._stage.moveto(y = y)
			out = self._daq.read()
			intsignal = out['IntSphere']['Mean']
			ref = out['Reference']['Mean']
			ydata[idx] = self._baselineCorrectionRoutine(wavelengths = wavelength, signal = intsignal, reference = ref)
		self._mono.closeShutter()
		self._stage.moveto(x = x0, y = y0) #return to original position

		if plot:
			fig, ax = subplot(2,1)
			ax[0].plot(allx, xdata)
			ax[0].xlabel('X Position (mm)')
			ax[0].ylabel('Reflectance at {0:d} nm'.format(wavelength))
			ax[0].title.set_text('X Scan')

			ax[1].plot(ally, ydata)
			ax[1].xlabel('Y Position (mm)')
			ax[1].ylabel('Reflectance at {0:d} nm'.format(wavelength))
			ax[1].title.set_text('Y Scan')
			plt.show()
		# return the centroid, width/bounds if found
		
		# HERE add code to find sample area based on the variation of reflectance

	def scanArea(self, label, wavelengths, xsize, ysize, xsteps = 21, ysteps = 21, x0 = None, y0 = None, export = True, verbose = False):
		# clean up wavelengths input
		wavelengths = np.array(wavelengths)

		if self._stage is None:
			self.connectStage() # connect stage
			self._stage.gohome()
		if self._daq is None:
			self.connect() # connect mono and daq

		self._stage.gotocenter() #go to center position, where sample is centered on integrating sphere port. Almost definitely need to remove this line later (we want to be centered at the sample center, which may shift and should be determined by .findArea)
		currentx, currenty = self._stage.position # return position
		if x0 is None:
			x0 = currentx
		if y0 is None:
			y0 = currenty

		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((xsteps, ysteps, len(wavelengths)))

		firstscan = True
		lastscan = False
		reverse=-1 # for snaking
		for xidx, x in tqdm(enumerate(allx), desc = 'Scanning X', total = allx.shape[0], leave = False):
			reverse=reverse*(-1)
			for yidx, y in tqdm(enumerate(ally), desc = 'Scanning Y', total = ally.shape[0], leave = False):
				if xidx == xsteps-1 and yidx == ysteps-1:
					lastScan = True
				# Condition to map in a snake pattern rather than coming back to first x point
				if reverse > 0: #go in the forward direction
					self._stage.moveto(x = x, y = y)
					signal, reference = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					data[xidx, yidx, :] = self._baselineCorrectionRoutine(wavelengths, signal, reference)
				else: # go in the reverse direction
					self._stage.moveto(x = x, y = ally[ysteps-1-yidx])
					signal,reference = self._scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					data[xidx, ysteps-1-yidx, :]=self._baselineCorrectionRoutine(wavelengths, signal, reference) # baseline correction
				firstscan = False

		if export:
			output = {
				'Label': label,
				'Date': datetime.date.today().strftime('%Y/%m/%d'),
				'Time': datetime.datetime.now().strftime('%H:%M:%S'),
				'X': allx.tolist(),
				'Y': ally.tolist(),
				'Wavelengths': wavelengths.tolist(),
				'Reflectance': data.tolist()
			}
			
			# export as a hfile
			
			# export as a json file
			fpath = os.path.join(self.outputdir, label + '.json')
			with open(fpath, 'w') as f:
				json.dump(output, f)

	# internal methods
	def _baselineCorrectionRoutine(self, wavelengths, signal, reference):
		if self.__baselineTaken == False:
			raise ValueError("Take baseline first")

		corrected = np.zeros(wavelengths.shape)
		for idx, wl in enumerate(wavelengths):
			meas = signal[idx]/reference[idx]
			#pdb.set_trace()
			bl_idx = np.where(self.__baseline['Wavelengths'] == wl)[0]
			corrected[idx] = (meas-self.__baseline['Dark']) / (self.__baseline['Light'][bl_idx]-self.__baseline['Dark']) 

		return corrected

	def _scanroutine(self, wavelengths, firstscan = True, lastscan = True):
		self._mono.goToWavelength(wavelengths[0])
		if firstscan:
			self._mono.openShutter()

		signal = np.zeros(wavelengths.shape)
		ref = np.zeros(wavelengths.shape)
		for idx, wl in tqdm(enumerate(wavelengths), total = wavelengths.shape[0], desc = 'Scanning {0:.1f}-{1:.1f} nm'.format(wavelengths[0], wavelengths[-1]), leave = False):
			self._mono.goToWavelength(wl)
			out = self._daq.read()
			signal[idx] = out['IntSphere']['Mean']
			ref[idx] = out['Reference']['Mean']
		
		if lastscan:
			self._mono.closeShutter()

		return signal, ref

	### Save method to dump measurement to hdf5 file. Currently copied from PL code, need to fit this to the mapping data.
	# def _save(self, samplename = None, note = None, outputdirectory = None):
	# 	## figure out the sample directory, name, total filepath
	# 	if samplename is not None:
	# 		self.sampleName = samplename

	# 	if outputdirectory is not None:
	# 		self.outputDirectory = outputdirectory
	# 	if not os.path.exists(self.outputDirectory):
	# 		os.mkdir(self.outputDirectory)

	# 	fids = os.listdir(self.outputDirectory)
	# 	sampleNumber = 1
	# 	for fid in fids:
	# 		if 'frgPL' in fid:
	# 			sampleNumber = sampleNumber + 1

	# 	if self.sampleName is not None:
	# 		fname = 'frgPL_{0:04d}_{1}.h5'.format(sampleNumber, self.sampleName)
	# 	else:
	# 		fname = 'frgPL_{0:04d}.h5'.format(sampleNumber)
	# 		self.sampleName = ''

	# 	fpath = os.path.join(self.outputDirectory, fname)

	# 	## build each category in h5 file

	# 	### example dataset saved to _dataBuffer by .takeMeas
	# 	# meas = {
	# 	# 	'sample': 	self.sampleName,
	# 	# 	'date': 	measdatetime.strftime('%Y-%m-%d'),
	# 	# 	'time':		measdatetime.strftime('%H:%M:%S'),
	# 	# 	'cameraFOV':self.__fov,
	# 	# 	'bias':		self.bias,
	# 	# 	'laserpower': self.laserpower,
	# 	# 	'saturationtime': self.saturationtime,
	# 	# 	'numIV':	self.numIV,
	# 	# 	'numframes':self.numframes,
	# 	# 	'v_meas':	v,
	# 	# 	'i_meas':	i,
	# 	# 	'image':	im,
	# 	# }

	# 	numData = len(self.__dataBuffer)

	# 	data = {}
	# 	for field in self.__dataBuffer[0].keys():
	# 		data[field] = []
	# 	### field to store normalized PL images
	# 	# if self._spotmap is not None:
	# 	# 	data['image_norm'] = []

	# 	for meas in self.__dataBuffer:
	# 		for field, measdata in meas.items():
	# 			data[field].append(measdata)
	# 			### normalize PL images here
	# 			# if field is 'image' and self._spotmap is not None:
	# 			# 	data['image_norm']


	# 	## write h5 file

	# 	with h5py.File(fpath, 'w') as f:
	# 		# sample info
	# 		info = f.create_group('/info')
	# 		info.attrs['description'] = 'Metadata describing sample, datetime, etc.'
			
	# 		temp = info.create_dataset('name', data = self.sampleName.encode('utf-8'))
	# 		temp.attrs['description'] = 'Sample name.'

	# 		date = info.create_dataset('date', data = np.array([x.encode('utf-8') for x in data['date']]))
	# 		temp.attrs['description'] = 'Measurement date.'

			
	# 		temp = info.create_dataset('time', data =  np.array([x.encode('utf-8') for x in data['time']]))
	# 		temp.attrs['description'] = 'Measurement time of day.'


	# 		# measurement settings
	# 		settings = f.create_group('/settings')
	# 		settings.attrs['description'] = 'Settings used for measurements.'

	# 		temp = settings.create_dataset('vbias', data = np.array(data['bias']))
	# 		temp.attrs['description'] = 'Nominal voltage bias set by Kepco during measurement.'

	# 		temp = settings.create_dataset('laserpower', data = np.array(data['laserpower']))
	# 		temp.attrs['description'] = 'Fractional laser power during measurement. Calculated as normalized laser current (max current = 55 A). Laser is operated at steady state.'

	# 		temp = settings.create_dataset('sattime', data = np.array(data['saturationtime']))
	# 		temp.attrs['description'] = 'Saturation time for laser/bias conditioning prior to sample measurement. Delay between applying condition and measuring, in seconds.'

	# 		temp = settings.create_dataset('numIV', data = np.array(data['numIV']))
	# 		temp.attrs['description'] = 'Number of current/voltage measurements averaged by Kepco when reading IV.'

	# 		temp = settings.create_dataset('numframes', data = np.array(data['numframes']))
	# 		temp.attrs['description'] = 'Number of camera frames averaged when taking image.'

	# 		if self._sampleOneSun is not None:
	# 			suns = [x/self._sampleOneSun for x in data['laserpower']]
	# 			temp = settings.create_dataset('suns', data = np.array(suns))
	# 			temp.attrs['description'] = 'PL injection level in terms of suns. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

	# 		# calibrations
	# 		calibrations = f.create_group('/calibrations')
	# 		calibrations.attrs['description'] = 'Instrument calibrations to be used for data analysis.'

	# 		temp = calibrations.create_dataset('fov', data = np.array(data['cameraFOV']))
	# 		temp.attrs['description'] = 'Camera field of view dimensions, in microns.'

	# 		if self._spotMap is not None:
	# 			temp = calibrations.create_dataset('spot', data = np.array(self._spotMap))
	# 			temp.attrs['description'] = 'Map of incident optical power across camera FOV, can be used to normalize PL images.'

	# 		if self._sampleOneSunSweep is not None:
	# 			temp = calibrations.create_dataset('onesunsweep', data = np.array(self._sampleOneSunSweep))
	# 			temp.attrs['description'] = 'Laser current vs photocurrent, measured for this sample. Column 1: fractional laser current. Column 2: total photocurrent (Isc), NOT current density (Jsc). Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

	# 			temp = calibrations.create_dataset('onesun', data = np.array(self._sampleOneSun))
	# 			temp.attrs['description'] = 'Fractional laser current used to approximate a one-sun injection level. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

	# 			temp = calibrations.create_dataset('onesunjsc', data = np.array(self._sampleOneSunJsc))
	# 			temp.attrs['description'] = 'Target Jsc (NOT Isc) used to approximate a one-sun injection level. Only present if sample was calibrated with .findOneSun to match measured Isc to provided expected value, presumably from solar simulator JV curve.'

	# 		# raw data
	# 		rawdata = f.create_group('/data')
	# 		rawdata.attrs['description'] = 'Raw measurements taken during imaging'

	# 		temp = rawdata.create_dataset('image', data = np.array(data['image']), chunks = True, compression = 'gzip')
	# 		temp.attrs['description'] = 'Raw images acquired for each measurement.'

	# 		temp = rawdata.create_dataset('v', data = np.array(data['v_meas']))
	# 		temp.attrs['description'] = 'Voltage measured during measurement'

	# 		temp = rawdata.create_dataset('i', data = np.array(data['i_meas']))
	# 		temp.attrs['description'] = 'Current (not current density!) measured during measurement'

	# 		temp = rawdata.create_dataset('irr_ref', data = np.array(data['irradiance_ref']))
	# 		temp.attrs['description'] = 'Measured irradiance @ photodetector during measurement. Note that the photodetector is offset from the sample FOV. Assuming that the laser spot is centered on the sample, this value is lower than the true sample irradiance. This value should be used in conjunction with a .spotMap() calibration map.'			

	# 	print('Data saved to {0}'.format(fpath))
	# 	if reset:
	# 		self.samplename = None

	# 		print('Note: sample name has been reset to None')
			

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
		self.connectStage()
		self.takeBaseline(wave)
		input('Place stage on integrating sphere: press enter to scan')
		self.takeScan("test",wave,True,False,False) # green stage
		input('Place mini module on sphere: press enter to scan')
		self.takeScan("test",wave,True,False,False) # minimodule