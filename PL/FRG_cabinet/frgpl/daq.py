## module for communication with OSTech laser controller

import serial
from PyDAQmx.DAQmxTypes import *

class daq:
	def __init__(self, port = 'COM1'):
		self.connect(port = port)	


	def connect(self, port = 'COM1'):
		self.__handle = serial.Serial(port)
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def acquire(self):
		read = int32()
		data = numpy.zeros((1000,), dtype=numpy.float64)
		DAQmxReadAnalogF64(taskHandle,1,10.0,
		    DAQmx_Val_GroupByChannel,data,1,byref(read),None)
