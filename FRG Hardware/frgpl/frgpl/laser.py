## module for communication with OSTech laser controller

import serial
import time

class laser:
	def __init__(self, port = 'COM13'):
		self.__maxcurrent = 55000.0
		self.__wavelength = 808
		self.connect(port = port)	
		## diffuser orientation
		#self._theta = 298
		#self._x = None	
		#self._y = None
		#self._z = None
		#self._d = None

	def connect(self, port = 'COM13'):
		self.__handle = serial.Serial()
		self.__handle.port = port
		self.__handle.timeout = 2
		self.__handle.open()
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def checkInterlock(self):
		interlockStatus = False

		while interlockStatus == False:
			self.__handle.flushInput()
			self.__handle.write('GS\r'.encode())
			time.sleep(0.01)
			for i in range(self.__handle.in_waiting):
				line = self.__handle.read()	#read but only keep the last hex sent
			binary = bin(line[-1])
			interlockStatus = bool(int(binary[-1]))	#first bit = 1 if interlock is satisfied, otherwise = 0

			if not interlockStatus:
				input('Interlock is not satisfied - check that the door is closed.\nPress Enter to check again.')		

		return interlockStatus

	def on(self):
		self.checkInterlock()	
		self.__handle.write('LR\r'.encode())
		return True

	def off(self):
		self.__handle.write('LS\r'.encode())
		self.__handle.readline()
		return True

	def set(self, power):
		#set power to some fraction of the maximum current. No PWM 
		if (power > 1) or (power < 0):
			return False
		else:
			current = self.__maxcurrent * power
			self.__handle.write('LCT {0:.1f}\r'.format(current).encode())
			return True


