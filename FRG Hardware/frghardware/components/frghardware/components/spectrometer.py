import time
import numpy as np
import stellarnet_driver3 as sn #usb driver

class Spectrometer:
	def __init__(self, address=0):
		self.id, self.wl = sn.array_get_spec(address)
		self.integrationtime = 100 #ms
		self.numscans = 1 #one scan per spectrum
		self.smooth = 1 #smoothing factor, units unclear

	@property
	def integrationtime(self):
		return self.__integrationtime
	@property.setter
	def integrationtime(self, t):
		self.id['device'].set_config(int_time=t)
		self.__integrationtime = t
	
	@property
	def numscans(self):
		return self.__numscans
	@property.setter
	def numscans(self, n):
		self.id['device'].set_config(scans_to_avg=n)
		self.__numscans = n

	@property
	def smooth(self):
		return self.__smooth
	@property.setter
	def smooth(self, n):
		self.id['device'].set_config(x_smooth=n)
		self.__smooth = n
		
	def acquire(self, wl=None):
		'''
		acquires a spectrum from the usb spectrometer
		'''
		if wl is None:
			wl = self.wl
	    spectrum = sn.array_spectrum(self.id, wl)
	    return spectrum

