## module for communication with Keithley 2401 source-meter

import visa
import numpy as np

class keithley:
	def __init__(self, port = 'GPIB2::20::INSTR'):
		self.__maxcurrent = 5
		self.__maxvoltage = 1
		self.__mode = 'VOLT'
		self.__on = False
		self.connect(port = port)	

	def _setter_helper(x, valid_inputs):
		if any([x == v for v in valid_inputs]):
			return True
		else:
			errorstr = 'Invalid input {}, value unchanged. Valid inputs are'.format(x)
			for v in valid_inputs[:-1]:
				errorstr += ' {},'.format(v)
			errorstr += ' {}.'.format(valid_inputs[-1])
			print(errorstr)	
			return False

	@property
	def source_mode(self):
		x = self.__handle.write(':SOUR:FUNC?')
		return x
	@source_mode.setter
	def source_mode(self, x):
		x = str.upper(x)
		valid_inputs = ['VOLT', 'CURR']
		if _setter_helper(x, valid_inputs)
			self.__handle.write(':SOUR:FUNC {}'.format(x))

	@property
	def source_delay(self):
		x = self.__handle.write(':SOUR:DEL?')
		return x
	@source_delay.setter
	def source_delay(self, x):
		self.__handle.write(':SOUR:DEL {0:f}'.format(x))

	@property
	def sense_mode(self):			
		x = self.__handle.write(':SENSE:FUNC?')
		return x
	@sense_mode.setter
	def sense_mode(self, x, y):
		x = str.upper(x)
		y = str.upper(y)
		if _setter_helper(x, ['VOLT', 'CURR']) and _setter_helper(y, ['DC', 'AC']):
			self.__handle.write(':SENSE:FUNC \'{}:{}\''.format(x,y))

	@property
	def format_element(self):
		x = self.__handle.write(':FORM:ELEM?')
		return x
	@format_element.setter
	def format_element(self, x):
		# if type(x) is str:
		# 	x = [x]
		if _setter_helper(x, ['VOLT', 'CURR', 'RES']):
			self.__handle.write(':FORM:ELEM {}'.format(x))
	


	@property
	def terminals(self):			
		x = self.__handle.write(':ROUT:TERM?')
		return x
	@terminals.setter
	def terminals(self, x):
		x = str.upper(x)
		if _setter_helper(x, ['FRONT', 'REAR']):
			self.__handle.write(':ROUT:TERM {}'.format(x))


	@property
	def voltage_limit(self):			
		x = self.__handle.write(':SENS:VOLT:PROT?')
		return x
	@voltage_limit.setter
	def voltage_limit(self, x):
		self.__handle.write(':SENSE:VOLT:PROT {0:f}'.format(x))


	@property
	def current_limit(self):			
		x = self.__handle.write(':SENS:CURR:PROT?')
		return x
	@current_limit.setter
	def current_limit(self, x):
		self.__handle.write(':SENSE:CURR:PROT {0:f}'.format(x))

	@property
	def current_limit(self):			
		x = self.__handle.write(':SENS:CURR:PROT?')
		return x
	@current_limit.setter
	def current_limit(self, x):
		self.__handle.write(':SENSE:CURR:PROT {0:f}'.format(x))

	@property
	def sense_4wire(self):			
		x = self.__handle.write(':SYST:RSEN?')
		return x
	@sense_4wire.setter
	def sense_4wire(self, x):
		if type(x) is not bool:
			print('Error: input must be True or False')
		else:
			if x:
				self.__handle.write(':SYST:RSEN ON')
			else:
				self.__handle.write(':SYST:RSEN OFF')

	@property
	def voltage(self):
		x = self.__handle.write(':SOUR:VOLT?')
		return x
	@voltage.setter
	def voltage(self, x):
		self.__handle.write(':SOUR:VOLT {0:f}'.format(x))



	def connect(self, port = 'GPIB2::20::INSTR'):
		self.__rm = visa.ResourceManager()
		self.__handle = rm.open_resource(port)
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
		self.__handle.write(':OUTP ON')
		self.__on = True
		return True

	def off(self):
		self.__handle.write(':OUTP OFF')
		self.__on = False
		return True

	def reset(self):
		self.__handle.write('*RST')


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
			self.__handle.write('MEAS:VOLT?\n'.encode())
			raw = self.__handle.readline()
			voltage[idx] = clean(raw)

			self.__handle.write('MEAS:CURR?\n'.encode())
	
			raw = self.__handle.readline()
			current[idx] = clean(raw)

			vmeas = round(np.mean(voltage), 5)
			imeas = round(np.mean(current), 5)
		return vmeas, imeas



