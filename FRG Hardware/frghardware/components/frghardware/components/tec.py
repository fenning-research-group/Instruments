## module for communication with Omega temperature controller

import serial
import numpy as np
import codecs

class Omega:
	def __init__(self, port, address = 1):
		self.connect(port = port, address = address)	
		
	@property
	def setpoint(self):
		self.__setpoint = self.__setpoint_get()
		return self.__setpoint

	@setpoint.setter
	def setpoint(self, x):
		if self.__setpoint_set(x):
			self.__setpoint = x
			return True
		else:
			self.__setpoint = self.__setpoint_get()
			print('Error changing set point - set point is still {0} C'.format(self.__setpoint))
			return False

	@property
	def temperature(self):
		return self.__temperature_get()
	
	def connect(self, port, address = 1):
		self.__handle = serial.Serial()
		self.__handle.port = port
		self.__handle.timeout = 2
		self.__handle.parity = 'E'
		self.__handle.bytesize = 7
		self.__handle.baudrate = 9600
		self.__handle.open()
		
		#configure communication bits
		self.__address = self.__numtohex(address)	#convert to hex, for use in communication <addr>
		self.__end = b'\r\n'	#end bit <etx>

		#read current setpoint
		# self.__setpoint = self.__setpoint_get()
		# self.__setpoint = None

		return True
	
	def disconnect(self):
		self.__handle.close()
		return True

	def __temperature_get(self):
		numWords = 1

		payload = self.__build_payload(
			command = 3,
			dataAddress = 1000,
			content = numWords
			)
		self.__handle.write(payload)
		response = self.__handle.readline()

		data = int(response[7:-4], 16) * 0.1	#response given in 0.1 C

		return round(data, 2)	#only give two decimals, rounding error gives ~8 decimal places of 0's sometimes

	def __setpoint_get(self):
		numWords = 1

		payload = self.__build_payload(
			command = 3,
			dataAddress = 1001,
			content = numWords
			)
		self.__handle.write(payload)
		response = self.__handle.readline()

		data = int(response[7:-4], 16) * 0.1	#response given in 0.1 C

		return data		

	def __setpoint_set(self, setpoint):
		setpoint = round(setpoint * 10)	#need to give integer values of 0.1 C

		payload = self.__build_payload(
			command = 6,
			dataAddress = 1001,
			content = setpoint
			)
		self.__handle.write(payload)
		response = self.__handle.readline()

		if response == payload:
			return True
			self.__setpoint = setpoint
		else:
			return False

	### helper methods
	def __numtohex(self, num):
		# return codecs.encode(str.encode('{0:02d}'.format(num)), 'hex_codec')
		return '{0:02X}'.format(num).encode()

	def __build_payload(self, command, dataAddress, content):
		def calculateChecksum(payload):
			numHexValues = int(len(payload)/2)
			hexValues = [int(payload[2*i : (2*i)+2], 16) for i in range(numHexValues)]
			checksum_int = 256 - sum(hexValues)%256 	#drop the 0x convention at front, we only want the last two characters
			checksum = '{0:02X}'.format(checksum_int) 

			return str.upper(checksum).encode()

		payload = self.__address
		payload = payload + self.__numtohex(command)
		payload = payload + str.encode(str(dataAddress))
		payload = payload + '{0:04X}'.format(content).encode()
		
		# calculate checksum from current payload
		chksum =calculateChecksum(payload)
		
		# complete the payload
		payload = payload + chksum
		payload = payload + self.__end
		payload = b':' + payload  	#should start with ":", just held til the end to not interfere with checksum calculation

		return payload
