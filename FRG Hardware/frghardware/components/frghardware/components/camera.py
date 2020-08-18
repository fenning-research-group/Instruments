## module for communication with OSTech laser controller

import serial
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.axes_grid1 import make_axes_locatable
import time
from scipy.signal import medfilt
from tqdm import tqdm
import cv2
from functools import partial
# import threading

class Hayear:
	def __init__(self, address = 0):
		self._resolution = [1080, 1920]
		self.__bufferSize = 5
		# self.__queue = None
		self.connect(address = address)
	
	def connect(self, address):
		self.cap = cv2.VideoCapture(address)
		self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[1])
		self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[0])	
	
		return True

	def disconnect(self):
		try:
			self.cap.release()
		except:
			pass

		return True

	@property
	def gain(self):
		self.__gain = self.cap.get(cv2.CAP_PROP_GAIN)
		return self.__gain
	@gain.setter
	def gain(self, g):
		self.cap.set(cv2.CAP_PROP_GAIN, g)
		self.__gain = g

	@property
	def gamma(self):
		self.__gamma = self.cap.get(cv2.CAP_PROP_GAMMA)
		return self.__gamma
	@gain.setter
	def gamma(self, g):
		self.cap.set(cv2.CAP_PROP_GAMMA, g)
		self.__gamma = g

	def capture(self, numframes = 10, imputeHotPixels = False, verbose = False):
		raw = np.zeros((numframes, self._resolution[0], self._resolution[1], 3))
		for idx in tqdm(range(numframes), desc = 'Acquiring Images', leave = False):
			for _ in range(self.__bufferSize - 1): #dump the buffer to acquire the most recent image
				self.cap.grab()
			ret, currentframe = self.cap.read()
			raw[idx] = cv2.cvtColor(currentframe, cv2.COLOR_BGR2RGB)/255 #cv2 reads RGB channels as BGR, this puts it back to RGB

		avg = np.mean(raw, axis = 0)
		std = np.std(raw, axis = 0)

		if imputeHotPixels:
			mask = avg > (avg.mean() + 3*avg.std())	#flag values 3 std devs over the mean
			medvals = medfilt(avg, 3)	#3x3 median filter
			avg[mask] = medvals[mask]

		if verbose:
			return dict(avg = avg, std = std, raw = raw)
		else:
			return avg

	def preview(self):
		# def animate(i, im):
		# 	ax.clear()
		# 	_, _, img = self.capture(numframes = 1)
		# 	im.set_data(img)
		# 	# cb.set_clim((img.min(), img.max()))

		# def handle_close(evt, cam = self._cam):
		# 	plt.ioff()

		# plt.ioff()
		# fig, ax = plt.subplots()
		# _, _, img = self.capture()
		# im = ax.imshow(img)
		# #divider = make_axes_locatable(ax)
		# #cax = divider.append_axes('right', size='5%', pad=0.05)
		# ani = animation.FuncAnimation(fig, partial(animate, im = im), interval=100, blit = True) 
		# fig.canvas.mpl_connect('close_event', lambda x: handle_close(x, cam = self._cam))

		# plt.ion()
		# plt.show()

		while(True):
		# Capture frame-by-frame
			ret, frame = self.cap.read()
			if ret:
				# Our operations on the frame come here
				gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

				# Display the resulting frame
				cv2.imshow('frame',gray)
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break
		cv2.destroyAllWindows()

	# read frames as soon as they are available, keeping only most recent one
	# def _reader(self):
	# 	while True:
	# 		ret, frame = self.cap.read()
	# 		if not ret:
	# 			break
	# 		self.__queue = frame