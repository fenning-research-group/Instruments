import numpy as np
import matplotlib as plt
import os
import serial
import time
from camera import camera
from stage import stage
from kepco import kepco
from daq import daq
from laser import laser

class control:

	def __init__(self, kepcoport = 'COM5',laserport = 'COM1'):
		# hardware properties
		self.kepcoport = kepcoport
		self.laserport = laserport
		self.__laserON = False
		self.__kepcoON = False
		self.__cameraON = False

		# measurement settings
		self._bias = 0			#bias applied to sample
		self._laserpower = 0	#current supplied to laser ###may replace this with n_suns, if calibration is enabled
		self._saturationtime = 0.5	#delay between applying voltage/illumination and beginning measurement
		self._numIV = 10		#number of IV measurements to average
		self._numframes = 50	#number of image frames to average

	def connect(self):
		### connect to flir camera
		self._camera = camera()

		# connect to kepco
		maxkepcocurrent = 3 	#max current in amps

		self._kepco = kepco()
		
		# Connect to OSTECH Laser
		max_laser_current = 55000	#mA

		self._laser = laser()

		### connect to the dataq

		self._daq = daq()
	
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

	def setmeas(self,
		bias = None,
		laserpower = None,
		saturationtime = None,
		numIV = None,
		numframes = None):

		if bias is None:
			bias = self._bias
		if laserpower is None:
			laserpower = self._laserpower
		if saturationtime is None:
			saturationtime = self._saturationtime
		if numIV is None:
			numIV = self._numIV
		if numframes is None:
			numframes = self._numframes

		result = self._kepco.set(voltage = bias)
		if result:
			self._bias = bias
		else:
			print('Error setting kepco')
			# return False

		result = self._laser.set(power = laserpower)

		if result:
			self._laserpower = laserpower
		else:
			print('Error setting laser')
			# return False

		self._numIV = numIV
		self._numframes = numframes

	def takemeas(self, lastmeasurement = True):
		if not self.__laserON and self._laserpower > 0:
			self._laser.on()
			self.__laserON = True
		if not self.__kepcoON and self._bias is not 0:
			self._kepco.on()	#turn on the kepco source
			self.__kepcoON = True

		time.sleep(self._saturationtime)

		#take image, take IV meas during image
		im, _, _ = self._camera.capture(frames = self._numframes, imputeHotPixels = True)
		v, i = self._kepco.read(counts = self._numIV)

		if self.__laserON and lastmeasurement:
			self._laser.off()
			self.__laserON = False
		if self.__kepcoON and lastmeasurement:
			self._kepco.off()
			self.__kepcoON = False

		return im, v, i
	
	def findonesun(self, jsc, area):
		### finds fraction laser power for which measured jsc = target value from solar simulator JV testing.
		# jsc: short circuit current density in mA/cm^2 (positive)
		# area: active area cm^2
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
		
		return p(isc), laserpowers, laserjsc	#return laser power to match target jsc




