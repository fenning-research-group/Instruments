## module for communication with OSTech laser controller

import serial
import time

class Laser808:
	def __init__(self, port = 'COM13'):
		self.__maxcurrent = 55000.0
		self.__wavelength = 808
		self.connect(port = port)	
		for bit in [0x4000, 0x0008, 0x8000]:
			self.__handle.write('GMC {0}\r'.format(bit).encode())	#set laser to desired communication protocol.
			time.sleep(0.02)

		while self.__handle.in_waiting > 0:
			self.__handle.flushInput()
			time.sleep(0.02)

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
		maxAttempts = 5

		attempt = 0
		while interlockStatus == False and attempt < maxAttempts:
			try:
				while self.__handle.in_waiting > 0:
					self.__handle.flushInput()
				self.__handle.write('GS\r'.encode())
				time.sleep(0.01)
				line = self.__handle.readline().decode('utf-8')
				status = line.split('\r')[-2].split(' ')[-1]
				if int(status) % 2 == 1:
					interlockStatus = True
				if not interlockStatus:
					input('Interlock is not satisfied - check that the door is closed.\nPress Enter to check again.')		
				attempt = 0
			except:
				attempt = attempt + 1
				interlockStatus = False
				
		return interlockStatus

	def on(self):
		self.checkInterlock()	
		self.__handle.write('LR\r'.encode())
		line = self.__handle.readline().decode('utf-8')

		return True

	def off(self):
		self.__handle.write('LS\r'.encode())
		while self.__handle.in_waiting > 0:
			self.__handle.flushInput()
		return True

	def set(self, power):
		#set power to some fraction of the maximum current. No PWM 
		if (power > 1) or (power < 0):
			return False
		else:
			current = self.__maxcurrent * power
			self.__handle.write('LCT {0:.1f}\r'.format(current).encode())
			return True


