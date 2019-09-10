## module for communication with Omega temperature controller

import serial
import numpy as np
import codecs

class tec:


	def __init__(self, port = 'COM12', address = 1):
		self.connect(port = port, address = address)	

	@property
	def setpoint(self):
		return self.__setpoint

	@getter.setpoint
	def setpoint(self):
		return self.__setpoint

	@setter.setpoint
	def setpoint(self, x):
		if self.setSetPoint(x):
			self.__setpoint = x
			return True
		else:
			print('Error changing set point - set point is still {0} C'.format(self.__setpoint))
			return False


	def connect(self, port = 'COM12', address = 1):
		self.__handle = serial.Serial()
		self.__handle.port = port
		self.__handle.timeout = 2
		self.__handle.parity = 'E'
		self.__handle.bytesize = 7
		self.__handle.baudrate = 9600
		self.__handle.open()
		
		#configure communication bits
		self.__address = self.numtohex(address)	#convert to hex, for use in communication <addr>
		self.__end = b'\r\n'	#end bit <etx>

		#read current setpoint
		self.__setpoint = self.getSetPoint()

		return True
	
	def disconnect(self):
		self.__handle.close()
		return True

	def getTemperature(self):
		numWords = 1

		payload = self.buildPayload(
			command = 3,
			dataAddress = 1000,
			content = numWords
			)
		self.__handle.write(payload)
		response = self.__handle.read(response)

		data = int(response[9:-4], 16) * 0.1	#response given in 0.1 C

		return data

	def getSetPoint(self):
		numWords = 1

		payload = self.buildPayload(
			command = 3,
			dataAddress = 1001,
			content = numWords
			)
		self.__handle.write(payload)
		response = self.__handle.read(response)

		data = int(response[9:-4], 16) * 0.1	#response given in 0.1 C

		return data		

	def setSetPoint(self, setpoint):
		setpoint = round(setpoint * 10)	#need to give integer values of 0.1 C

		payload = self.buildPayload(
			command = 6,
			dataAddress = 1001,
			content = setpoint
			)
		self.__handle.write(payload)
		response = self.__handle.read(response)

		if response[9:-4] is 'FF00':
			return True
		else:
			return False

	### helper methods
	def numtohex(self, num):
		# return codecs.encode(str.encode('{0:02d}'.format(num)), 'hex_codec')
		return '{0:02X}'.format(num).encode()

	def buildPayload(self, command, dataAddress, content):
		def calculateChecksum(payload):
			numHexValues = int(len(payload)/2)
			hexValues = [int(payload[2*i : (2*i)+2], 16) for i in range(numHexValues)]
			checksum = hex(256 - sum(hexValues))[-2:]	#drop the 0x convention at front, we only want the last two characters

			return str.upper(checksum).encode()

		payload = self.__address
		payload = payload + self.numtohex(command)
		payload = payload + str.encode(str(dataAddress))
		payload = payload + '{0:04X}'.format(content).encode()
		
		# calculate checksum from current payload
		chksum =calculateChecksum(payload)
		
		# complete the payload
		payload = payload + chksum
		payload = payload + self.__end
		payload = b':' + payload  	#should start with ":", just held til the end to not interfere with checksum calculation

		return payload
