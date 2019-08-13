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

class control(object):
	def __init__(self, outputdir = None, dwelltime = 0.1):
		self.outputdir = outputdir
		self.dwelltime = dwelltime
		self.__baselineTaken = False
		self.__baseline = {}

	def connect(self):
		#connect to spectrometer hardware
		self._mono = mono()
		self._daq = daq(dwelltime = self.dwelltime)

	def connectStage(self):
		#connect to stage hardware
		self._stage = stage()

	def takeBaseline(self, wavelengths):
		#light baseline
		self.__baseline['Wavelengths'] = wavelengths
		self.__baseline['LightRaw'], self.__baseline['LightRefRaw'] = self.scanroutine(wavelengths)
		self.__baseline['Light'] = [self.__baseline['LightRaw'][x] / self.__baseline['LightRefRaw'][x] for x in range(len(self.__baseline['LightRaw']))]
		
		#dark baseline
		out = self._daq.read()
		self.__baseline['DarkRaw'] = out['IntSphere']['Mean']
		self.__baseline['DarkRefRaw'] = out['Reference']['Mean']
		self.__baseline['Dark'] = self.__baseline['DarkRaw'] / self.__baseline['DarkRefRaw']

		self.__baselineTaken = True

	def takeScan(self, label, wavelengths, plot = False, export = True, verbose = False):
		data = {
			'Label': label,
			'Date': datetime.date.today().strftime('%Y/%m/%d'),
			'Time': datetime.datetime.now().strftime('%H:%M:%S'),
			'Wavelengths': wavelengths,
			'Reflectance': [],
			'DwellTime': self.dwelltime
		}

		signal, reference = self.scanroutine(wavelengths)
		data['Reflectance'] = self.baselinecorrectionroutine(wavelengths, signal, reference)

		if verbose:
			data['Verbose'] = {
				'Signal': signal,
				'Reference': reference,
				'Baseline': self.__baseline
			}

		if export and self.outputdir is not None:
			fpath = os.path.join(self.outputdir, label + '.json')
			with open(fpath, 'w') as f:
				json.dump(data, f)

		if plot:
			plt.plot(data['Wavelengths'],data['Reflectance'])
			plt.xlabel('Wavelength (nm)')
			plt.ylabel('Reflectance (%)')
			plt.title(label)
			plt.show()

	def findArea(self, wavelength, xsize = 30, ysize = 30, xsteps = 21, ysteps = 21, plot = True, export = False):
		x0, y0 = self._stage.position
		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)
		
		self._mono.goToWavelength(wavelength)
		
		self._stage.moveto(x = allx[0], y = y0)
		self._mono.openShutter()		
		xdata = []
		for x in allx:
			self._stage.moveto(x = x)
			out = self._daq.read()
			reflectance = self.baselinecorrectionroutine(wavelengths = wavelength, signal = out['IntSphere']['Mean'], reference = out['Reference']['Mean'])
			xdata.append(reflectance)
		self._mono.closeShutter()

		self._stage.moveto(x = x0, y = ally[0])
		self._mono.openShutter()		
		ydata = []
		for y in ally:
			self._stage.moveto(y = y)
			out = self._daq.read()
			reflectance = self.baselinecorrectionroutine(wavelengths = wavelength, signal = out['IntSphere']['Mean'], reference = out['Reference']['Mean'])
			ydata.append(reflectance)
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

	def scanArea(self, label, wavelengths, xsize, ysize, xsteps = 21, ysteps = 21, export = True, verbose = False):
		x0, y0 = self._stage.position
		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((xsteps, ysteps, len(wavelengths)))

		firstscan = True
		lastscan = False
		for xidx, x in enumerate(allx):
			for yidx, y in enumerate(ally):
				if xidx == xsteps-1 and yidx == ysteps-1:
					lastScan = True
				data[xidx, yidx, :] = self.scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
				firstscan = False

		if export:
			output = {
				'Label': label,
				'Date': datetime.date.today().strftime('%Y/%m/%d'),
				'Time': datetime.datetime.now().strftime('%H:%M:%S'),
				'X': allx,
				'Y': ally,
				'Wavelengths': wavelengths,
				'Reflectance': data
			}

			fpath = os.path.join(self.outputdir, label + '.json')
			with open(fpath, 'w') as f:
				json.dump(output, f)

	# internal methods
	def baselinecorrectionroutine(self, wavelengths, signal, reference):
		corrected = []
		for idx, wl in enumerate(wavelengths):
			meas = signal[idx]/reference[idx]

			bl_idx = self.__baseline['Wavelengths'].index(wl)
			corrected.append((meas-self.__baseline['Dark']) / (self.__baseline['Light'][bl_idx]-self.__baseline['Dark']))

		return corrected

	def scanroutine(self, wavelengths, firstscan = True, lastscan = True):
		self._mono.goToWavelength(wavelengths[0])
		if firstscan:
			self._mono.openShutter()

		signal = []
		ref = []
		for wl in wavelengths:
			self._mono.goToWavelength(wl)
			out = self._daq.read()
			signal.append(out['IntSphere']['Mean'])
			ref.append(out['Reference']['Mean'])
		
		if lastscan:
			self._mono.closeShutter()

		return signal, ref