import numpy as np
import matplotlib.pyplot as plt
import os
import serial
import time
import json
from stage import stage
from mono import mono
from daq import daq
import datetime
import pdb

class control(object):
	def __init__(self, outputdir = None, dwelltime = 0.1):
		self.outputdir = outputdir
		self.dwelltime = dwelltime
		self.__baselineTaken = False
		self.__baseline = {}
		self._stage=object()
		self._daq=object(dwelltime = dwelltime)

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
		#light baseline
		self.__baseline['Wavelengths'] = wavelengths
		self.__baseline['LightRaw'], self.__baseline['LightRefRaw'] = self.scanroutine(wavelengths)
		self.__baseline['Light'] = [self.__baseline['LightRaw'][x] / self.__baseline['LightRefRaw'][x] for x in range(len(self.__baseline['LightRaw']))]
		
		#dark baseline
		out = self._daq.read()
		self.__baseline['DarkRaw'] = out['IntSphere']['Mean']
		self.__baseline['DarkRefRaw'] = out['Reference']['Mean']
		self.__baseline['Dark'] = self.__baseline['DarkRaw'] / self.__baseline['DarkRefRaw']
		
		#pdb.set_trace()

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
			plt.ylabel('Reflectance')
			plt.title(label)
			plt.show()

	def findArea(self, wavelength, xsize = 30, ysize = 30, xsteps = 6, ysteps = 6, plot = True, export = False):
	# method to find sample edges
		#wavelength must be entered as a list
		self.connectStage() # connect stage
		self.connect() # connect mono
		self._stage.gotocenter()
		self._stage.postmove()
		x0, y0 = self._stage.position
		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)
		
		self._mono.goToWavelength(wavelength[0])
		
		self._stage.moveto(x = allx[0], y = y0)
		self._mono.openShutter()		
		xdata = []
		for x in allx:
			self._stage.moveto(x = x)
			out = self._daq.read()
			intsignal=[] # for consistency: signal must be a list for baselinecorrectionroutine and signal is a list in scanroutine
			ref=[]
			intsignal.append(out['IntSphere']['Mean'])
			ref.append(out['Reference']['Mean'])
			#pdb.set_trace()
			#reflectance = self.baselinecorrectionroutine(wavelengths = wavelength, signal = intsignal, reference = ref)
			#xdata.append(reflectance)
		self._mono.closeShutter()

		self._stage.moveto(x = x0, y = ally[0])
		self._mono.openShutter()
		ydata = []
		for y in ally:
			self._stage.moveto(y = y)
			out = self._daq.read()
			#reflectance = self.baselinecorrectionroutine(wavelengths = wavelength, signal = out['IntSphere']['Mean'], reference = out['Reference']['Mean'])
			#ydata.append(reflectance)
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

	def scanArea(self, label, wavelengths, xsize, ysize, xsteps = 21, ysteps = 21, export = True, verbose = False):
		self.connectStage() # connect stage
		# self._stage.gohome() # home stage and update position (in stage.py)
		# set x0 and y0 in the middle for testing purposes
		#x0=50
		#y0=50
		self._stage.gotocenter()
		x0, y0 = self._stage.position # return position
		allx = np.linspace(x0 - xsize/2, x0 + xsize/2, xsteps)
		ally = np.linspace(y0 - ysize/2, y0 + ysize/2, ysteps)

		data = np.zeros((xsteps, ysteps, len(wavelengths)))

		firstscan = True
		lastscan = False
		reverse=-1 # for snaking
		for xidx, x in enumerate(allx):
			reverse=reverse*(-1)
			for yidx, y in enumerate(ally):
				if xidx == xsteps-1 and yidx == ysteps-1:
					lastScan = True
				# Condition to map in a snake pattern rather than coming back to first x point
				if reverse > 0: #go in the forward direction
					self._stage.moveto(x = x, y = y)
					signal, reference = self.scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					data[xidx, yidx, :] = self.baselinecorrectionroutine(wavelengths, signal, reference)
				else: # go in the reverse direction
					self._stage.moveto(x = x, y = ally[ysteps-1-yidx])
					signal,reference = self.scanroutine(wavelengths = wavelengths, firstscan = firstscan, lastscan = lastscan)
					data[xidx, ysteps-1-yidx, :]=self.baselinecorrectionroutine(wavelengths, signal, reference) # baseline correction
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
			
			# export as a hfile
			
			# export as a text file
			#fpath = os.path.join(self.outputdir, label + '.json')
			#with open(fpath, 'w') as f:
			#	json.dump(output, f)

	# internal methods
	def baselinecorrectionroutine(self, wavelengths, signal, reference):
		corrected = []
		if self.__baselineTaken == False:
			raise ValueError("Take baseline first")

		for idx, wl in enumerate(wavelengths):
			meas = signal[idx]/reference[idx]
			#pdb.set_trace()
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

	def measspectra(self):
		wave=np.linspace(1700,2000,151,dtype=int)
		wave=wave.tolist()
		self.connect()
		self.connectStage()
		self.takeBaseline(wave)
		input()
		self.takeScan("test",wave,True,False,False) # green stage
		input()
		self.takeScan("test",wave,True,False,False) # minimodule