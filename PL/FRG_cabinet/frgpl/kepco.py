## module for communication with OSTech laser controller

import serial
import re
import numpy as np

class kepco:
	def __init__(self, port = 'COM4'):
		self.__maxcurrent = 5
		self.__maxvoltage = 1
		self.__mode = 'VOLT'
		self.__on = False
		self.connect(port = port)	


	def connect(self, port = 'COM4'):
		self.__handle = serial.Serial(port)
		self.__handle.write('SYST:REM ON\n'.encode())
		self.__handle.write('VOLT:RANG {0:.2f}\n'.format(self.__maxvoltage).encode())
		self.__handle.write('FUNC:MODE {0:s}\n'.format(self.__mode).encode())
		self.__handle.write('CURR {0:d}\n'.format(self.__maxcurrent).encode())	#set current limit to +/- 5 amps
		return True

	def disconnect(self):
		self.__handle.write('SYST:REM OFF\n'.encode())
		self.__handle.close()
		return True

	def on(self):
		self.__handle.write('OUTP ON\n'.encode())	
		self.__on = True
		return True

	def off(self):
		self.__handle.write('OUTP OFF\n'.encode())	
		self.__on = False
		return True

	def set(self, voltage = None, current = None):
		### ADD CHECK FOR LIMITS
		if voltage is not None:
			if self.__mode is not 'VOLT':
				self.__handle.write('FUNC:MODE VOLT\n'.encode())
				self.__mode = 'VOLT'
			self.__handle.write('VOLT {0:0.4f}\n'.format(voltage).encode())
		elif current is not None:
			if self.__mode is not 'CURR':
				self.__handle.write('FUNC:MODE CURR\n'.encode())
				self.__mode = 'CURR'
			self.__handle.write('CURR {0:0.4f}\n'.format(current).encode())
		return True

	def read(self, counts = 10):
		current = np.zeros((counts,1))
		voltage = np.zeros((counts,1))

		def clean(string):
			string = string.decode('utf-8')
			string = re.sub('\x11', '', string)
			string = re.sub('\x13', '', string)
			string = re.sub('\r', '', string)
			string = re.sub('\n', '', string)
			
			value = float(string)
			return value

		for idx in range(counts):
			self.__handle.write('MEAS:VOLT?\n'.encode())
			raw = self.__handle.readline()
			voltage[idx] = clean(raw)

			self.__handle.write('MEAS:CURR?\n'.encode())
			raw = self.__handle.readline()
			current[idx] = clean(raw)

		return np.mean(voltage), np.mean(current)



