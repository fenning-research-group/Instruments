## module for communication with OSTech laser controller

import serial
import numpy as np
from PyDAQmx import *

class daq:
	def __init__(self, port = 'Dev2/ai2'):
		self.__range = (-10.0, 10.0)
		self.__rate = 10000	#Hz
		self.__counts = 1000
		self.__singleAnalogReadTask = None
		self.connect(port = port)	


	def connect(self, port = 'Dev2/ai2'):
		self.__photodetector = port.encode()
		#create single datapoint read task
		self.configureSingleAcquisition()
		return True

	def configureSingleAcquisition(self, counts = None, rate = None):
		if not counts:
			counts = self.__counts

		if not rate:
			rate = self.__rate

		self.__singleAnalogReadTask = Task()
		self.numread = int32()
		self.data = np.zeros((self.__counts,), dtype=np.float64)	
		
		self.__singleAnalogReadTask.CreateAIVoltageChan(self.__photodetector,"",DAQmx_Val_Cfg_Default,self.__range[0],self.__range[1],DAQmx_Val_Volts,None)
		self.__singleAnalogReadTask.CfgSampClkTiming("",float(self.__rate),DAQmx_Val_Rising,DAQmx_Val_FiniteSamps,self.__counts)
		
		self.__rate = rate
		self.__counts = counts
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def acquire(self, counts = None, rate = None):
		if not counts:
			counts = self.__counts

		if not rate:
			rate = self.__rate
			
		if (counts != self.__counts) or (rate != self.__rate):
			self.configureSingleAcquisition(counts, rate)

		try:
			# DAQmx Start Code
			self.__singleAnalogReadTask.StartTask()

			# DAQmx Read Code
			self.__singleAnalogReadTask.ReadAnalogF64(self.__counts,self.__range[1],DAQmx_Val_GroupByChannel,self.data,self.__counts,self.numread,None)
			# print "Acquired %d points"%read.value

		except DAQError as err:
			print("DAQmx Error: {0:s}".format(err))
		
		self.__singleAnalogReadTask.StopTask()

		avg = np.mean(self.data)
		std = np.std(self.data)

		return avg, std, self.data

		# DAQmxReadAnalogF64(taskHandle,1,10.0,
		#     DAQmx_Val_GroupByChannel,data,1,byref(read),None)
