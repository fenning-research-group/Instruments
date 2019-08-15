## module for communication with OSTech laser controller

import serial

class laser:
	def __init__(self, port = 'COM1'):
		self.__maxcurrent = 55000.0
		self.__wavelength = 808
		self.connect(port = port)	
		## diffuser orientation
		#self._theta = 298
		#self._x = None	
		#self._y = None
		#self._z = None
		#self._d = None

	def connect(self, port = 'COM1'):
		self.__handle = serial.Serial(port)
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def checkInterlock(self):





	def on(self):
		self.checkInterlock()	
		self.__handle.write('LR')
		return True

	def off(self):
		self.__handle.write('LS')
		return True

	def setPower(self, power):
		#set power to some fraction of the maximum current. No PWM 
		if (power >= 1) or (power < 0):
			return False
		else:
			current = self.__maxcurrent * power
			self.__handle.write('LCT {0:.1f}'.format(current))
			return True


