import NKTP_DLL as nktdll

## TO DO (ctrl-f TODO)
#
# 1. connect to hardware
#		- figure out com port for each, fill in portName fields (ctrl-f INSERTDEFAULT)
#		- code currently checks to see if device is found, I think it receives a hex value from deviceGetAllTypes, which is then compared to an expected number for compact (74) or select (66)
#		- need to get both the com port and the device address (0-15, I guess multiple devices can share one com port).
#			- i think the code already grabs thisfrom deviceGetAllTypes. this number is the second argument when writing to hardware registry to control things
#
# 2. select
#		- three things to set per each of 8 channels: wavelength, amplitude, gain. 
#		- what should the gain be left at by default- 100%, or 0%? currently sets to 0
#		- how do we select the proper AOTF? Maybe by connecting to select on its own (you can connect to two device #'s - 66 = select + rf driver (currently being used), or 67 = only select')
#			- looks like theres an option to RF switch with 67, hopefully this is the way to switch them. Attempt to do this automatically under select.connect(), line ~217
#		- determine optimum RF power to avoid side bands taking over main optical band (refer to manual)
#			- make 3d dataset of wavelength, RF power, measured signal at int sphere detector
#			- at each wavelength, find first local maximum in rf power vs measured signal plot. this is the optimum RF power
#			- store a csv/json/something in the library file with table of optimum powers
#			- add a step to read this in when initializing
#			- when using setAOTF, make amplitude default to optimum power per wavelength when value is not specified
#				- interpolate or find nearest neighbor of specified wavelength from calibration, use this RF power.

class compact(object):

	def __init__(self, portName = 'INSERTDEFAULTCOMPACTPORTHERE'):		# TODO: add compact port here as default
		self.__handle = None	#will be overwritten upon connecting, set back to None upon disconnecting
		if self.connect():
			self.setPower(powerLevel = 50) #default starting power level, 0-100 = 0-100% power
			self.setPulseFrequency(pulseFrequency = 1000)	#default pulse frequency set to 1 kHz
			self.setTrigger(mode = 0)	#turn off external trigger mode

		self.emissionOn = False

	def connect(self, portName = 'INSERTDEFAULTCOMPACTPORTHERE'):
		result, devList = nktdll.deviceGetAllTypes(portName)
		for devId in range(0, len(devList)):
			if int(devList[devId], 16) == 74:		# TODO portData should hold a hex value corresponding to device found at this port. Compact = 74, select = 66. 
				# portData = nktdll.openPorts(portName, 0, 0) # TODO I think the port is still open after running nktdll.deviceGetAllTypes(portName), but if not we can reconnect here
				print('Connected to NKT COMPACT')
				self.__handle = portName
				self.__address = devId
				return True
		#if we made it here, we didnt find the COMPACT at the supplied portName
		closePorts(portName)
		print('NKT COMPACT not found at port {0}. Not connected.'.format(portName))
		return False

	def disconnect(self):
		if self.__handle is not None:
			self.off()	#turn off laser before disconnecting
			nktdll.closePorts(self.__handle)
			self.__handle = None
			self.__address = None

	def on(self):
		if not self.emissionOn:
			result = nktdll.registerWriteU8(self.__handle, self.__address, 0x30, 1, -1) # check whether 1 should be sent as an hexadecimal value. Might need to make a function to convert to hex values
			if result == 0:
				self.emissionOn = True
				return True
			else:
				print('Error encountered when trying to turn laser emission on:', RegisterResultTypes(result))
				return False
		else:
			return True

	def off(self):
		if self.emissionOn:
			result = nktdll.registerWriteU8(self.__handle, self.__address, 0x30, 0, -1)
			if result == 0:
				self.emissionOn = False
				return True
			else:
				print('Error encountered when trying to turn laser emission off:', RegisterResultTypes(result))
				return False
		
		else:
			return True

	def setPower(self, powerLevel): # might actually require an hexadecimal value, in that case we'll need a function to convert to hex
		### takes U8 integer input to set laser power.
		# Value = powerLevel %
		if type(powerLevel) != int:
			if type(powerlevel) == float:
				print('Note: only integer values 0-100 allowed as power settings: rounding float {0:f} to nearest int {1:d}').format(powerLevel, round(powerLevel))
				powerLevel = round(powerLevel)	#can only pass U8 int, rounding off floats here
			else:
				print('TypeError: only integer values 0-100 allowed as power settings.')
				return False

		if powerLevel > 100:
			print('Note: only integer values 0-100 allowed as power settings: reducing {0:d} to 100.'.format(powerLevel))
			powerLevel = 100
		if powerLevel < 0:
			print('Note: only integer values 0-100 allowed as power settings: increasing {0:d} to 0.'.format(powerLevel))
			powerLevel = 0

		result = nktdll.registerWriteU8(self.__handle, self.__address, 0x3E, powerLevel, -1) # call hex conversion function here
		if result == 0: # 0 if successful
			self.powerLevel = powerLevel
			return True
		else:
			print('Error encountered when trying to change laser power level:', RegisterResultTypes(result))
			return False

	def setPulseFrequency(self, pulseFrequency):
		### takes U32 integer input to set pulse frequency. 
		# Value = 0.001 * pulseFrequency kHz.
		if type(pulseFrequency) != int:
			if type(pulseFrequency) == float:
				print('Note: only 32-bit integer values allowed as frequency settings: rounding float {0:f} to nearest int {1:d}').format(pulseFrequency, round(pulseFrequency))
				pulseFrequency = round(pulseFrequency)	#can only pass U32 int, rounding off floats here
			else:
				print('TypeError: only 32-bit integer values allowed as frequency settings.')
				return False

		if pulseFrequency > 2147483647:		### Can revisit this if we find a maximum frequency setting that matters. Currently capping at 32 bit value, shouldnt really matter
			print('Note: only 32-bit integer values allowed as frequency settings: reducing {0:d} to 2147483647.'.format(pulseFrequency))
			pulseFrequency = 2147483647

		if pulseFrequency < 0:
			print('Note: only positive 32-bit integer values allowed as frequency settings: increasing {0:d} to 1.'.format(pulseFrequency))
			pulseFrequency = 1

		result = nktdll.registerWriteU32(self.__handle, self.__address, 0x3E, pulseFrequency, -1)
		if result == 0:
			self.pulseFrequency = pulseFrequency
			return True
		else:
			print('Error encountered when trying to change laser internal pulse frequency:', RegisterResultTypes(result))
			return False

	def setTrigger(self, mode = None, setPoint = None):
		### mode takes boolean input to set trigger mode. if True, laser set to be externally triggered. 
		### setPoint takes U16 integer input to set trigger setpoint (threshold voltage to trigger laser). V = 0.001 * setpoint
		success = True

		# handle mode
		if mode is not None:
			if mode:
				mode = 1
			else:
				mode = 0

			result = nktdll.registerWriteU8(self.__handle, self.__address, 0x31, mode, -1)
			if result == 0:
				self.trigger.mode = mode
				success = True
			else:
				print('Error encountered when trying to change laser trigger mode:', RegisterResultTypes(result))
				success = False

		# handle setpoint
		if setPoint is not None:
			if type(setPoint) != int:
				if type(setPoint) == float:
					print('Note: only integer values 0-4000 allowed as trigger voltage settings: rounding float {0:f} to nearest int {1:d}').format(setPoint, round(setPoint))
					powerLevel = round(setPoint)	#can only pass U8 int, rounding off floats here
				else:
					print('TypeError: only integer values 0-4000 allowed as trigger voltage settings.')
					return False

			if setPoint > 4000:
				print('Note: only integer values 0-4000 (0-4 V) allowed as trigger voltage settings: reducing {0:d} to 100.'.format(setPoint))
				setPoint = 4000
			if setPoint < 0:
				print('Note: only integer values 0-4000 (0-4 V) allowed as trigger voltage settings: increasing {0:d} to 0.'.format(setPoint))
				setPoint = 0

			result = nktdll.registerWriteU16(self.__handle, self.__address, 0x24, mode, -1)
			if result == 0:
				self.trigger.mode = mode
				success = True
			else:
				print('Error encountered when trying to change laser trigger voltage:', RegisterResultTypes(result))
				success = False

		return success

class select(object):

	def __init__(self, portName = 'INSERTDEFAULTSELECTPORTHERE'):		# TODO: add select port here as default
		self.__handle = None	#will be overwritten upon connecting, set back to None upon disconnecting
		self.__defaultWavelengths = [1700, 1750, 1800, 1850, 1900, 1902, 1950, 2000]	#default values to assign to unspecified wavelength selections
		self._wavelengths = [None] * 8
		self._amplitudes = [None] * 8
		self._gains = [None] * 8
		self._range = [None] * 2
		self.__maxRange = (1100, 2000) #set the min/max wavelength range allowed by AOTF here
		if self.connect():
			self.set(wavelength = self.__defaultWavelengths, amplitude = [0] * 8)
			self.wavelengthRange()	#set range to default range

			# self.setPower(powerLevel = 50) #default starting power level, 0-100 = 0-100% power
			# self.setPulseFrequency(pulseFrequency = 1000)	#default pulse frequency set to 1 kHz
			# self.setTrigger(mode = 0)	#turn off external trigger mode

		# self.emissionOn = False

	def connect(self, portName = 'INSERTDEFAULTSELECTPORTHERE'):
		result, devList = nktdll.deviceGetAllTypes(portName)
		success = 0
		for devId in range(0, len(devList)):
			if int(devList[devId], 16) == 66:		#TODO portData should hold a hex value corresponding to device found at this port. Compact = 74, select = 67 (? not sure why its here on its own), select + rf driver = 66. 
				# portData = nktdll.openPorts(portName, 0, 0) # TODO I think the port is still open after running nktdll.deviceGetAllTypes(portName), but if not we can reconnect here
				print('Connected to NKT SELECT + RF (66)')
				self.__handle = portName
				self.__address = devId
				success = success + 1
			if int(devList[devId], 16) == 67:		#TODO portData should hold a hex value corresponding to device found at this port. Compact = 74, select = 67 (? not sure why its here on its own), select + rf driver = 66. 
				# portData = nktdll.openPorts(portName, 0, 0) # TODO I think the port is still open after running nktdll.deviceGetAllTypes(portName), but if not we can reconnect here
				print('Connected to NKT SELECT (67)')
				self.__handle = portName
				self.__address2 = devId
				success = success + 1
				result = nktdll.registerWriteU8(self.__handle, self.__address2, 0x34, 1, -1)	#TODO set to 1, assuming that this corresponds to the IR aotf. may need to change this to properly select the IR aotf
				if result != 0:
					print('Error encountered when trying to direct RF to IR AOTF:', RegisterResultTypes(result))
					success = False
								
		if success == 2:	#found both addresses, no issues setting to IR aotf
			return True
		else:
			closePorts(portName)
			print('Not connected.'.format(portName))
			return False

	def disconnect(self):
		if self.__handle is not None:
			nktdll.closePorts(self.__handle)
			self.__handle = None
			self.__address = None
			self.__address2 = None

	def on(self):
		if not self.rfOn:
			result = nktdll.registerWriteU8(self.__handle, self.__address, 0x30, 1, -1)
			if result == 0:
				self.rfOn = True
				return True
			else:
				print('Error encountered when trying to turn rf power on:', RegisterResultTypes(result))
				return False
		else:
			return True

	def off(self):
		if self.rfOn:
			result = nktdll.registerWriteU8(self.__handle, self.__address, 0x30, 0, -1)
			if result == 0:
				self.rfOn = False
				return True
			else:
				print('Error encountered when trying to turn rf power off:', RegisterResultTypes(result))
				return False
		
		else:
			return True

	def setAOTF(self, wavelength, amplitude = None, gain = None):
		### takes input to set wavelength. 
		# takes input 0-1 to set amplitude
		# takes input 0-1 to set gain (input * 0.1 = %)
		
		## tidy up inputs
		if type(wavelength) is not list:
			wavelength = [wavelength] 
		wavelength = round(wavelength * 1000) 	#when talking to select, (0.001 * input = wavelength (nm)). 
		
	 	if amplitude is not None:
			if amplitude is not list:
				amplitude = [amplitude]
			for idx, a in amplitude:
				if a > 1:
					amplitude[idx] = 1000
					print('Note: amplitude values should be supplied in range 0-1. Setting {0} to 1'.format(a))
				elif a < 0:
					amplitude[idx] = 0
					print('Note: amplitude values should be supplied in range 0-1. Setting {0} to 0'.format(a))
				else:
					amplitude[idx] = round(a * 1000	)
		else:
			amplitude = [1000 for x in wavelength] #when talking to select,  (input * 0.1 = %. 1000 = 100%)

		if gain is not None:
			if gain is not list:
				gain = [gain]
			for idx, g in gain:
				if g > 1:
					gain[idx] = 1000
					print('Note: gain values should be supplied in range 0-1. Setting {0} to 1'.format(g))
				elif g < 0:
					gain[idx] = 0
					print('Note: gain values should be supplied in range 0-1. Setting {0} to 0'.format(g))
				else:
					gain[idx] = round(g * 1000	)
		else:
			gain = [0 for x in wavelength] #TODO when talking to select,  (input * 0.1 = %. 1000 = 100%)

		for idx in range(len(wavelength), 8):	#pad so all 8 wavelength channels are accounted for when talking to select
			wavelength = wavelength + self.__defaultWavelengths[idx]
			amplitude = amplitude + [0]
			gain = gain + [0]

		# set all the wavelengths, amplitudes, and gains
		success = True

		for idx, wl, a, g in enumerate(zip(wavelength, amplitude, gain)):
			# if type(wl) != int:
			# 	if type(wl) == float:
			# 		print('Note: only integer values 0-100 allowed as power settings: rounding float {0:f} to nearest int {1:d}').format(powerLevel, round(powerLevel))
			# 		powerLevel = round(powerLevel)	#can only pass U8 int, rounding off floats here
			# 	else:
			# 		print('TypeError: only integer values 0-100 allowed as power settings.')
			# 		return False
			result = nktdll.registerWriteU32(self.__handle, self.__address, hex(int('0x9{0}'.format(idx),16)), wl, -1)
			if result == 0:
				self._wavelengths[idx] = wl
			else:
				print('Error encountered when trying to change wavelength {0} to {1} nm:'.format(idx, wl/1000), RegisterResultTypes(result))
				success = False

			result = nktdll.registerWriteU16(self.__handle, self.__address, hex(int('0xB{0}'.format(idx),16)), a, -1)
			if result == 0:
				self._amplitudes[idx] = a
			else:
				print('Error encountered when trying to change amplitude {0} to {1}:'.format(idx, a/1000), RegisterResultTypes(result))
				success = False

			result = nktdll.registerWriteU16(self.__handle, self.__address, hex(int('0xC{0}'.format(idx),16)), g, -1)
			if result == 0:
				self._gains[idx] = g
			else:
				print('Error encountered when trying to change gain {0} to {1}:'.format(idx, g/1000), RegisterResultTypes(result))
				success = False

		return success


	def setWavelengthRange(self, wmin = None, wmax = None):
		## takes inputs in nm

		#revert to default bounds if none specified
		if wmin is None:
			wmin = self.__maxRange[0]
		if wmax is None:
			wmax = self.__maxRange[1]


		# set wavelength range
		success = True

		result = nktdll.registerWriteU32(self.__handle, self.__address, 0x34, wmin * 1000, -1)	#multiply by 1000 because compact reads input in terms of 0.001 nm
		if result == 0:
			self._range[0] = wmin
		else:
			print('Error encountered when trying to set wavelength range lower bound to {0} nm:'.format(wmin), RegisterResultTypes(result))
			success = False

		result = nktdll.registerWriteU32(self.__handle, self.__address, 0x35, wmax * 1000, -1)	#multiply by 1000 because compact reads input in terms of 0.001 nm
		if result == 0:
			self._range[1] = wmax
		else:
			print('Error encountered when trying to set wavelength range lower bound to {0} nm:'.format(wmax), RegisterResultTypes(result))
			success = False

		return success