## module for communication with Keithley 2401 source-meter

import visa
import numpy as np

class keithley:
	def __init__(self, port = 'GPIB2::20::INSTR'):
		self.__maxcurrent = 5
		self.__maxvoltage = 1
		self.__mode = 'VOLT'
		self.connect(port = port)	
		self.__handle.timeout = 0.5
		self.__handle.read_terminator = '\n'
		self.__handle.write_terminator = '\n'

	def errorcheck(self):
		x = self.__handle.write(':SYST:ERR?')
		code, explanation = x.split(',')
		if code == 0:
			return True
		else
			print('Error {}:{}'.format(code, explanation))
			return False
	### SOURCE COMMANDS
	@property
	def source_mode(self):
		self.__handle.write(':SOUR:FUNC?')
		response = self.__handle.read()
		return response	
	@source_mode.setter
	def source_mode(self, x):
		self.__handle.write(':SOUR:FUNC {}'.format(str.upper(x)))
		return self.errorcheck():
	
	@property
	def source_voltage(self):
		self.__handle.write(':SOUR:VOLT?')
		response = self.__handle.read()
		return response	
	@source_voltage.setter
	def source_voltage(self, x):
		self.__handle.write(':SOUR:VOLT {0:f}'.format(x))
		return self.errorcheck()

	@property
	def source_current(self):
		self.__handle.write(':SOUR:CURR?')
		response = self.__handle.read()
		return response
	@source_current.setter
	def source_current(self, x):
		self.__handle.write(':SOUR:CURR {0:f}'.format(x))
		return self.errorcheck()

	@property
	def source_delay(self):
		self.__handle.write(':SOUR:DEL?')
		response = self.__handle.read()
		return response
	@source_delay.setter
	def source_delay(self, x):
		self.__handle.write(':SOUR:DEL {0:f}'.format(x))
		return self.errorcheck

	### SENSE COMMANDS
	@property
	def sense_mode(self):			
		self.__handle.write(':SENSE:FUNC?')
		response = self.__handle.read()
		return response
	@sense_mode.setter
	def sense_mode(self, x, y):
		x = str.upper(x)
		y = str.upper(y)
		self.__handle.write(':SENSE:FUNC \'{}:{}\''.format(x,y))
		return self.errorcheck()

	@property
	def voltage_limit(self):			
		self.__handle.write(':SENS:VOLT:PROT?')
		response = self.__handle.read()
		return response
	@voltage_limit.setter
	def voltage_limit(self, x):
		self.__handle.write(':SENSE:VOLT:PROT {0:f}'.format(x))
		return self.errorcheck()

	@property
	def current_limit(self):			
		self.__handle.write(':SENS:CURR:PROT?')
		response = self.__handle.read()
		return response
	@current_limit.setter
	def current_limit(self, x):
		self.__handle.write(':SENSE:CURR:PROT {0:f}'.format(x))
		return self.errorcheck()

	@property
	def sense_4wire(self):			
		self.__handle.write(':SYST:RSEN?')
		response = self.__handle.read()
		return response
	@sense_4wire.setter
	def sense_4wire(self, x):
		if type(x) is not bool:
			print('Error: input must be True or False')
		else:
			if x:
				self.__handle.write(':SYST:RSEN ON')
			else:
				self.__handle.write(':SYST:RSEN OFF')
			return self.errorcheck()

	@property
	def averaging_filter(self):			
		self.__handle.write(':SENS:AVER:STAT?')
		response = self.__handle.read()
		print('Averaging Filter is {}'.format(response))
		if response is 'ON':
			self.__averagingfilteron = True
		else:
			self.__averagingfilteron = False
			return
		
		self.__handle.write(':SENS:AVER:TCON?')
		filtertype = self.__handle.read()
		self.__handle.write(':SENS:AVER:COUN?')
		filtercount = self.__handle.read()

		print('Type: {}\nCounts: {}'.format(filtertype, filtercount))
		return
	@averaging_filter.setter
	def averaging_filter(self, on = True, filtertype = 'REP', count = 10):
		if 'REP' in str.upper(filtertype):
			filtertype = 'REP'
		elif 'MOV' in str.upper(filtertype):
			filtertype = 'MOV'
		else:
			Exception('Filter type must be REPeat or MOVing!')
		if count < 1 or count > 100:
			Exception('Filter count must be between 1-100!')
		
		if on:
			self.__handle.write(':SENS:AVER:STAT ON')
			self.__handle.write(':SENS:AVER:TCON {}'.format(filtertype))
			self.__handle.write(':SENS:AVER:COUN {0:d}'.format(count))
		else:
			self.__handle.write(':SENS:AVER:STAT OFF')
		return self.errorcheck()


	### FORMAT COMMANDS
	@property
	def format_element(self):
		self.__handle.write(':FORM:ELEM?')
		response = self.__handle.read()
		return response
	@format_element.setter
	def format_element(self, x):
		if type(x) is str:
			allx = x
		else:
			allx = ''
			for x_ in x[:-1]:
				allx += '{},'.format(x_)
			allx += x[-1]

		self.__handle.write(':FORM:ELEM {}'.format(allx))
		success = self.errorcheck()
		if success:
			self.__valuelabels = allx

		return success

	### MISC COMMANDS
	@property
	def terminals(self):			
		self.__handle.write(':ROUT:TERM?')
		response = self.__handle.read()
		return response
	@terminals.setter
	def terminals(self, x):
		x = str.upper(x)
		self.__handle.write(':ROUT:TERM {}'.format(x))
		return self.errorcheck()

	### Basic usage COMMANDS
	def on(self):
		self.__handle.write(':OUTP ON')
		success = self.errorcheck():
		if success:
			self._on = True
		return success

	def off(self):
		self.__handle.write(':OUTP OFF')
		success = self.errorcheck():
		if success:
			self._on = False
		return success

	def acquire(self):
		if not self._on:
			print('Error: Keithley must be ON before data can be acquired!')
			return None
			
		response = self.__handle.read()
		readings = {}
		for k, v in zip(self.__valuelabels, response.split(',')):
			readings[k] = float(v)
		return readings

	def connect(self, port = 'GPIB2::20::INSTR'):
		self.__rm = visa.ResourceManager()
		self.__handle = rm.open_resource(port)

		self.__handle.write(':OUTP ?')
		self._on = self.__handle.read()

		self.__valuelabels = self.format_element

		return True

	def disconnect(self):
		# self.__handle.write(':SYST:REM OFF')
		self.__handle.close()
		return True

	def sweep_voltage(self, start, stop, steps, delay = 0.01, spacing = 'LIN'):
		if 'LIN' in str.upper(spacing):
			spacing = 'LIN'
		elif 'LOG' in str.upper(spacing):
			spacing = 'LOG'
		else:
			Exception('Invalid spacing - must be LINear or LOGarithmic!')

		self.__handle.write(':SENS:FUNC:CONC OFF') #unclear why we need this
		self.__handle.write(':SOUR:FUNC VOLT')
		self.__handle.write(':SENS:FUNC \'CURR:DC\'')
		self.__handle.write(':SOUR:VOLT:START {0:f}'.format(start))
		self.__handle.write(':SOUR:VOLT:STOP {0:f}'.format(stop))
		self.__handle.write(':SOUR:SWE:POIN {0:d}'.format(steps))
		self.__handle.write(':SOUR:SWE:DIRE UP') #go from start to stop
		self.__handle.write(':SOUR:VOLT:MODE SWE')


		if not self.errorcheck():
			Exception('Problem setting sweep parameters - sweep not performed.')

		self.__handle.write(':OUTP ON')
		self.__handle.write(':READ?')
		response = self.__handle.read()

		self.__handle.write('SOUR:VOLT:MODE FIX')
		self.errorcheck()

		return response


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

	# def set(self, voltage = None, current = None):
	# 	### ADD CHECK FOR LIMITS
	# 	if voltage is not None:
	# 		if self.__mode is not 'VOLT':
	# 			self.__handle.write('FUNC:MODE VOLT\n'.encode())
	# 			self.__mode = 'VOLT'
	# 			self.__handle.write('CURR {0:d}\n'.format(self.__maxcurrent).encode())
	# 		self.__handle.write('VOLT {0:0.4f}\n'.format(voltage).encode())
	# 	elif current is not None:
	# 		if self.__mode is not 'CURR':
	# 			self.__handle.write('FUNC:MODE CURR\n'.encode())
	# 			self.__mode = 'CURR'
	# 			self.__handle.write('VOLT {0:d}\n'.format(self.__maxvoltage).encode())
	# 		self.__handle.write('CURR {0:0.4f}\n'.format(current).encode())
	# 	return True

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



