## module for communication with OSTech laser controller

import serial
from PyDAQmx.DAQmxTypes import *

class daq:
	def __init__(self, port = 'COM1'):
		self.connect(port = port)	
		self.__photodetector = 'Dev2/ai0'
		self.__range = (-10, 10)
		self.__rate = 1000
		self.__counts = 1000

	def connect(self, port = 'COM1'):
		self.__handle = serial.Serial(port)
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def acquire(self, counts = self.__counts, rate = self.__rate):
		taskHandle = TaskHandle()
		read = int32()
		data = numpy.zeros((counts,), dtype=numpy.float64)		

		try:
			# DAQmx Configure Code
			DAQmxCreateTask("",byref(taskHandle))
			DAQmxCreateAIVoltageChan(taskHandle,self.__photodetector,"",DAQmx_Val_Cfg_Default,
				self.__range[0], self.__range[1],DAQmx_Val_Volts,None)
			DAQmxCfgSampClkTiming(taskHandle,"",10000.0,DAQmx_Val_Rising,DAQmx_Val_FiniteSamps,1000)

			# DAQmx Start Code
			DAQmxStartTask(taskHandle)

			# DAQmx Read Code
			DAQmxReadAnalogF64(taskHandle,1000,10.0,DAQmx_Val_GroupByChannel,data,1000,byref(read),None)

			# print "Acquired %d points"%read.value

		except DAQError as err:
			print "DAQmx Error: %s"%err
		finally:
			if taskHandle:
				# DAQmx Stop Code
				DAQmxStopTask(taskHandle)
				DAQmxClearTask(taskHandle)
			
		avg = np.mean(data)
		std = np.std(data)

		return avg, std, data

		# DAQmxReadAnalogF64(taskHandle,1,10.0,
		#     DAQmx_Val_GroupByChannel,data,1,byref(read),None)
