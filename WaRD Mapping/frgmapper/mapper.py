import numpy as np
import matplotlib as plt
import os
import serial
import time
import json
from stage import stage
from mono import mono
from daq import daq

class control:

	def __init__(outputdir = None, dwelltime = 0.1):
		self.__outputdir = outputdir
		self.dwelltime = dwelltime
		self.__spectrometerConnected = False
		self.__stageConnected = False
		self.__baselineTaken = False
		self.__baseline = {}

	def connect(self):
		#connect to spectrometer hardware
		self.__mono = mono()
		self.__daq = daq(dwelltime = self.dwelltime)

	def connectStage(self):
		#connect to stage hardware
		self.__stage = stage()

	def takeBaseline(self, wavelengths):
		#light baseline
		self.baseline['Wavelengths'] = wavelengths
		self.baseline['LightRaw'], self.baseline['LightRefRaw'] = self.scanroutine(wavelengths)
		self.baseline['Light'] = [self.baseline['LightRaw'][x] / self.baseline['LightRefRaw'][x] for x in range(len(self.baseline['LightRaw']))]
		
		#dark baseline
		out = self.__daq.read()
		self.baseline['DarkRaw'] = out['IntSphere']['Mean']
	    self.baseline['DarkRefRaw'] = out['Reference']['Mean']
	    self.baseline['Dark'] = self.baseline['DarkRaw'] / self.baseline['DarkRefRaw']

	    self.__baselineTaken = True


	def takeScan(self, label, wavelengths, plot = False, export = True):
		data = {
			'Label': label,
			'Date': datetime.date.today().strftime('%Y/%m/%d'),
			'Time': datetime.now().strftime('%H:%M:%S'),
			'Wavelengths': wavelengths,
			'Reflectance': [],
			'DwellTime': self.dwelltime
		}

		signal, reference = self.scanroutine(wavelengths)
		data['Reflectance'] = self.baselinecorrectionroutine(wavelengths, signal, reference)

		if export and self.__outputdir is not None:
			fpath = os.path.join(self.__outputdir, label + '.json')
			with open(fpath, 'w') as f:
				json.dump(data, fpath)

		if plot:
			plt.plot(data['Wavelengths'],data['Reflectance'])
			plt.xlabel('Wavelength (nm)')
			plt.ylabel('Reflectance (%)')
			plt.title(label)
			plt.show()

	def baselinecorrectionroutine(self, wavelengths, signal, reference):
		corrected = []
		for idx, wl in enumerate(wavelengths):
			meas = signal[idx]/reference[idx]

			bl_idx = self.baseline['Wavelengths'].index(wl)
			corrected.append((meas-self.baseline['Dark'][bl_idx]) / (self.baseline['Light'][bl_idx]-self.baseline['Dark'][bl_idx]))

		return corrected

	def scanroutine(self, wavelengths):
		self.__mono.goToWavelength(wavelengths[0])
		self.__mono.openShutter()

		signal = []
		ref = []
		for wl in wavelengths:
			self.__mono.goToWavelength(wl)
			out = self.__daq.read()
			signal.append(out['IntSphere']['Mean'])
			ref.append(out['Reference']['Mean'])

		self.__mono.closeShutter()


		return signal, ref



