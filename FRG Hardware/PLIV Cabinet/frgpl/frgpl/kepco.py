## module for communication with OSTech laser controller

import serial
import re
import numpy as np
import pdb

class kepco:
	def __init__(self, port = 'COM12'):
		self.__maxcurrent = 5
		self.__maxvoltage = 1
		self.__mode = 'VOLT'
		self.__on = False
		self.connect(port = port)	

	def connect(self, port = 'COM12'):
		self.__handle = serial.Serial(port,timeout=8)
		self.__handle.write('SYST:REM ON\n'.encode())
		self.__handle.write('VOLT:RANG {0:.2f}\n'.format(self.__maxvoltage).encode())
		self.__handle.write('FUNC:MODE {0:s}\n'.format(self.__mode).encode())
		self.__handle.write('CURR {0:d}\n'.format(self.__maxcurrent).encode())	#set current limit to +/- 5 amps
		#self.__handle.write('VOLT {0:d}\n'.format(0).encode()) # set voltage to 0 volts (solves some current compliance issue that appears sometime)

		# self.__handle.write('VOLT {0:d}\n'.format(self.__maxcurrent).encode())

		print(str("Max current set in kepco.connect to "+str(self.__maxcurrent)+" A."))
		#pdb.set_trace()
		# self.__handle.write('CURR:LIM:HIGH {0:.2E}\n'.format(5).encode()) # Set max current limit. klp manual page B-9 and point 6.7.1 p. 6-8
		# print("Max current limit set")
		# show high current limit
		#self.__handle.write('CURR:LIM:HIGH?\n'.encode()) # klp manual page B-9 and point 6.7.1 p. 6-8
		#rawmaxcurr = self.__handle.readline()
		#maxcurr = clean(rawmaxcurr)
		#print(str('high limit current: '+str(rawmaxcurr)))
		#pdb.set_trace()
		# show current protection limit (CURR:PROT)
		# self.__handle.write('CURR?\n'.encode()) # klp manual page B-9 and point 6.7.1 p. 6-8
		# currtest = self.__handle.readline()
		# #maxcurr = clean(rawmaxcurr)
		# print(str('set current value: '+str(currtest)))

		# self.__handle.write('CURR:PROT?\n'.encode()) # klp manual page B-9 and point 6.7.1 p. 6-8
		# currprot = self.__handle.readline()
		# #maxcurr = clean(rawmaxcurr)
		# print(str('current protection value: '+str(currprot)))

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
				self.__handle.write('CURR {0:d}\n'.format(self.__maxcurrent).encode())
			self.__handle.write('VOLT {0:0.4f}\n'.format(voltage).encode())
		elif current is not None:
			if self.__mode is not 'CURR':
				self.__handle.write('FUNC:MODE CURR\n'.encode())
				self.__mode = 'CURR'
				self.__handle.write('VOLT {0:d}\n'.format(self.__maxvoltage).encode())
			self.__handle.write('CURR {0:0.4f}\n'.format(current).encode())
		return True

	def read(self, counts = 10):
		maxAttempts = 5

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

		#kep._kepco__handle__write('CURR?MAX\n'.encode()) # get max current value set
		#self.__handle.write('CURR?MAX\n'.encode()) # get max current value set (note: this is the max achievable value in this model, not the compliance value!)
		#rawmaxcurr = self.__handle.readline()
		#maxcurr = clean(rawmaxcurr)
		#print(str('max current: '+str(maxcurr)))



		for idx in range(counts):
			attempts = 0
			success = False
			while attempts < maxAttempts and not success:
				try:
					self.__handle.write('MEAS:VOLT?\n'.encode())
					raw = self.__handle.readline()
					voltage[idx] = clean(raw)

					self.__handle.write('MEAS:CURR?\n'.encode())
			
					raw = self.__handle.readline()
					current[idx] = clean(raw)

					success = True
				except:
					attempts = attempts + 1

			vmeas = round(np.mean(voltage), 5)
			imeas = round(np.mean(current), 5)

		return vmeas, imeas



