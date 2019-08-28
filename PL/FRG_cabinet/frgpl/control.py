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
		self._kepcomode = 'VOLT'
		self._bias = 0			#bias applied to sample
		self._lasercurrent = 0	#current supplied to laser ###may replace this with n_suns, if calibration is enabled
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
	# def setmeas(self,
	# 	kepcomode = 'self._kepcomode',
	# 	bias = self._bias,
	# 	lasercurrent = self._lasercurrent,
	# 	saturationtime = self._saturationtime,
	# 	numIV = self._numIV,
	# 	numframes = self._numframes):

	# 	if kepcomode in ['I', 'CURR', 'OC', 'Open Circuit', 'opencircuit']:
	# 		self._kepcomode = b'CURR'
	# 	elif kepcomode in ['V', 'VOLT', 'SC', 'Short Circuit', 'shortcircuit']:
	# 		self._kepcomode = b'VOLT'
	# 	self.__kepco.write(b'FUNC:MODE ' + self._kepcomode)

	# 	if self._kepcomode is b'CURR':
	# 		self._bias = 0
	# 		if bias is not 0:
	# 			print('Cannot apply voltage bias while kepco is set to CURR mode: bias has been automatically adjusted from {0:d} to 0'.format(bias))
	# 	else:
	# 		self._bias = bias
	# 	self.__kepco.write(b'VOLT {0:d}'.format(self._bias))

	# 	if lasercurrent > self.__maxlasercurrent:
	# 		self._lasercurrent = self.__maxlasercurrent
	# 		print('Invalid laser current, too high: corrected from {0:d} to {1:d}'.format(lasercurrent, self.__maxlasercurrent))
	# 	elif lasercurrent < 0:
	# 		self._lasercurrent = 0
	# 		print('Invalid laser current, too low: corrected from {0:d} to 0'.format(lasercurrent))
	# 	else:
	# 		self._lasercurrent = lasercurrent
	# 	laserwrite(self.__laser, b'{0:d}.0'.format(self._lasercurrent))

	# 	self._numIV = numIV
	# 	self._numframes = numframes

	# def takemeas(self, lastmeasurement = True):
	# 	if not self.__laserON and self._lasercurrent > 0:
	# 		laserwrite(self.__laser, 'LR')	#turn on the laser (Laser Run)
	# 		self.__laserON = True
	# 	if not self.__kepcoON and self._kepcomode is 'VOLT' and self._bias is not 0:
	# 		self.__kepco.write('OUTP ON')	#turn on the kepco source
	# 		self.__kepcoON == True

	# 	time.sleep(self._saturationtime)

	# 	#take image, take IV meas during image

	# 	if self.__laserON and lastmeasurement:
	# 		laserwrite(self.__laser, 'LS')
	# 		self.__laserON = False
	# 	if self.__kepcoON and lastmeasurement:
	# 		self.__kepco.write('OUTP OFF')	#turn off the kepco source
	# 		self.__kepcoON = False

	def findonesun(self, jsc):
		laserpowers = np.linspace(0,0.5, 5)[1:]	#skip 0, lean on lower end to reduce incident power
		self._kepco.set(voltage = 0)

		laserjsc = np.zeros(len(laserpowers))		
		self._laser.on()
		for idx, power in enumerate(laserpowers):
			self._laser.set(power = power)
			time.sleep(self._saturationtime)
			_,laserjsc[idx] = self._kepco.read()
		self._laser.off()
		pfit = np.polyfit(laserjsc, laserpowers, 2)
		p = np.poly1d()	#polynomial fit object where x = measured jsc, y = laser power applied
		return p(jsc)	#return laser power to match target jsc




