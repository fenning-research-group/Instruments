import cv2
import matplotlib.pyplot as plt
import numpy as np
from .mono import mono
import time
from tqdm import tqdm

class PerovskiteCamera:
	def __init__(self):
		self._resolution = [1080, 1920]
		self.monoConnected = False
		self.connect()
	
	def connect(self):
		self.cap = cv2.VideoCapture(0) #assumes first camera is the target camera
		self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[1])
		self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[0])

		self.mono = mono()
	
	def disconnect(self):
		self.cap.release()
		self.mono.disconnect()

	def capture(self, numframes = 10, verbose = False):
		raw = np.zeros((numframes, self._resolution[0], self._resolution[1], 3))

		for idx in range(numframes):
			ret, currentframe = self.cap.read()
			raw[idx] = cv2.cvtColor(currentframe, cv2.COLOR_BGR2RGB) #cv2 reads RGB channels as BGR, this puts it back to RGB

		avg = np.mean(raw, axis = 0)
		std = np.std(raw, axis = 0)

		# if imputeHotPixels:
		# 	mask = avg > (avg.mean() + 3*avg.std())	#flag values 3 std devs over the mean
		# 	medvals = medfilt(avg, 3)	#3x3 median filter
		# 	avg[mask] = medvals[mask]

		if verbose:
			return {
				'avg': avg/255,
				'std': std/255,
				'raw': raw/255
			}
		else:
			return avg/255

	def calibrateColor(self, wlmin, wlmax, numwl = 10, numframes = 10, ROI = [0, 0, -1, -1]):
		wl = np.linspace(wlmin, wlmax, numwl)
		r = np.zeros((numwl,))
		g = np.zeros((numwl,))
		b = np.zeros((numwl,))

		self.mono.openShutter()
		time.sleep(1)

		for idx, wl_ in tqdm(enumerate(wl), total = numwl):
			self.mono.goToWavelength(wl_)
			im = self.capture(numframes = numframes)
			r[idx] = im[ROI[0]:ROI[2], ROI[1]:ROI[3], 0].mean()
			g[idx] = im[ROI[0]:ROI[2], ROI[1]:ROI[3], 1].mean()
			b[idx] = im[ROI[0]:ROI[2], ROI[1]:ROI[3], 2].mean()

		self.mono.closeShutter()

		output = {
			'wl': wl,
			'r': np.array(r),
			'g': np.array(g),
			'b': np.array(b),
			'mean': np.array([r,g,b]).mean(axis = 0)
		}
		return output