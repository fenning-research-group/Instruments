## module for communication with Omega temperature controller

import serial
import numpy as np
import codecs

class tec:
	def __init__(self, port = 'COM12', address = 1):
		self.connect(port = port, address = address)	


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

		return True

	def disconnect(self):
		self.__handle.close()
		return True


	### helper methods
	def numtohex(self, num):
		# return codecs.encode(str.encode('{0:02d}'.format(num)), 'hex_codec')
		return '{0:02X}'.format(num).encode()

	def buildPayload(self, command, dataAddress, numWords):
		def calculateChecksum(payload):
			numHexValues = int(len(payload)/2)
			hexValues = [int(payload[2*i : (2*i)+2], 16) for i in range(numHexValues)]
			checksum = hex(256 - sum(hexValues))[-2:]	#drop the 0x convention at front, we only want the last two characters

			return str.upper(checksum).encode()

		payload = self.__address
		payload = payload + self.numtohex(command)
		payload = payload + str.encode(str(dataAddress))
		payload = payload + str.encode(str('{0:04d}'.format(numWords)))
		
		# calculate checksum from current payload
		chksum =calculateChecksum(payload)
		
		# complete the payload
		payload = payload + chksum
		payload = payload + self.__end
		payload = b':' + payload  	#should start with ":", just held til the end to not interfere with checksum calculation

		return payload
