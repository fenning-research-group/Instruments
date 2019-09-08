## module for communication with Omega temperature controller

import serial
import numpy as np
import codecs

class tec:
	def __init__(self, port = 'COM12', address = 1):
		self.connect(port = port, address = address)	


	def connect(self, port = 'COM12', address = 1):
		self.__handle = serial.Serial()
		self.__handle.timeout = 2
		self.__handle.parity = 'E'
		self.__handle.bytesize = 7
		self.__handle.baudrate = 19200
		self.__handle.open()
		
		#configure communication bits
		self.__address = numtohex(address)	#convert to hex, for use in communication <addr>
		self.__end = b'\r\n'	#end bit <etx>

		return True

	def disconnect(self):
		self.__handle.close()
		return True


	### helper methods
	def numtohex(num):
		return codecs.encode(str.encode('{0:02d}'.format(num)), 'hex_codec')

	def buildPayload(self, command, dataAddress, numWords):
		payload = self.__address
		payload = payload + numtohex(command)
		payload = payload + str.encode(str(dataAddress))
		payload = payload + str.encode(str('{0:04d}'.format(numWords)))
		
		# calculate checksum from current payload
		chksum = sum([int(payload[2*i : (2*i)+2], 16) for i in range(int(len(payload)/2))]) 	#add all bits as decimal values
		chksum = hex(chksum % 256) #convert back to hex, only keep two bits
		chksum = codecs.encode(str.encode(chksum[-2:], 'hex_codec'))	#only consider the last bit for checksum

		# complete the payload

		payload = payload + chksum
		payload = payload + self.__end
		payload = b':' + payload  	#should start with ":", just held til the end to not interfere with checksum calculation

		return payload
