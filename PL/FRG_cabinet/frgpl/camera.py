## module for communication with OSTech laser controller

import serial
import os
import PySpin
import numpy as np
import matplotlib.pyplot as plt

class camera:
	def __init__(self, port = None):
		self.__system = PySpin.System.GetInstance()
	def connect(self, port = None):
		def setContinuousAcquisition(nodemap):
			### set acquisition mode to continuous. mode is left as continuous for both continous feed and snapping images, so we do it here. code from PySpin example "Acquisition.py"
			node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
			if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
				print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
				return False
			# Retrieve entry node from enumeration node
			node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
			if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
				print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
				return False
			# Retrieve integer value from entry node
			acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
			# Set integer value from entry node as new value of enumeration node
			node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
			return True

		def getResolution(cam):
			cam.BeginAcquisition()
			acquired = False
			while not acquired:
				image_result = cam.GetNextImage()
				if not image_result.IsIncomplete():
					acquired = True
			cam.EndAcquisition()

			width = image_result.GetWidth()
			height = image_result.GetHeight()
			return (height - 1, width)	#last column of pixels is dead - sensor has 512 columns, reports images with 513 columns. idk why

		cam_list = self.__system.GetCameras()
		self._cam = cam_list[0]	#assumes only one gigecam connected to computer
		self._cam.Init()
		self._cam.PixelFormat.SetValue(PySpin.PySpin.PixelFormat_Mono16)

		self._nodemap = self._cam.GetNodeMap()
		setContinuousAcquisition(self._nodemap)
		self._resolution = getResolution(self._cam)

		return True

	def disconnect(self):
		self._cam.DeInit()
		return True

	def snap(self, frames = 100):
		raw = np.zeros((self._resolution[0], self._resolution[1], frames))

		self._cam.BeginAcquisition()
		for idx in range(frames):
			acquired = False

			while not acquired:
				image_result = self._cam.GetNextImage()
				if not image_result.IsIncomplete():
					acquired = True

				img = image_result.Convert(PySpin.PixelFormat_Mono16, PySpin.HQ_LINEAR).GetNDArray()
				image_result.Release()
				raw[:, :, idx] = img[1:self._resolution[0]+1, :self._resolution[1]]	#throw away pixels outside of desired resolution (specifically one column is inactive in InGaAs camera)
		self._cam.EndAcquisition()

		avg = np.mean(raw, axis = 2)
		std = np.std(raw, axis = 2)


		return avg, std, raw

	# def preview(self):
		

