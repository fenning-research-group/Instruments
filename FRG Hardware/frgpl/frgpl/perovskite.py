import cv2
import matplotlib.pyplot as plt
import numpy as np

class PerovskiteCamera:
	def __init__(self):
		self._resolution = [1080, 1920]
		self.connect()
	
	def connect(self):
		self.cap = cv2.VideoCapture(0) #assumes first camera is the target camera
		self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[1])
		self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[0])
	
	def disconnect(self):
		self.cap.release()

	def capture(self, frames = 1):
		raw = np.zeros((self._resolution[0], self._resolution[1], frames))

		for idx in range(frames):
			ret, currentframe = self.cap.read()
			currentframe = cv2.cvtColor(currentframe, cv2.COLOR_BGR2RGB) #cv2 reads RGB channels as BGR, this puts it back to RGB
			raw[:,:,idx] = currenframe

		avg = np.mean(raw, axis = 2)
		std = np.std(raw, axis = 2)

		# if imputeHotPixels:
		# 	mask = avg > (avg.mean() + 3*avg.std())	#flag values 3 std devs over the mean
		# 	medvals = medfilt(avg, 3)	#3x3 median filter
		# 	avg[mask] = medvals[mask]

		return avg, std, raw

	def calibrateColor(self, wlmin, wlmax, numwl = 10, ROI = [0, 0, -1, -1], mono = True):
		from .mono import mono
		self.mono = mono()

		wl = np.linspace(wlmin, wlmax, numwl)
		r = np.zeros((numwl,))
		g = np.zeros((numwl,))
		b = np.zeros((numwl,))

		self.mono.openShutter()
		for idx, wl_ in enumerate(wl):
			self.mono.goToWavelength(wl_)
			im = self.capture()
			r[idx] = im[ROI, 0].mean()
			g[idx] = im[ROI, 1].mean()
			b[idx] = im[ROI, 2].mean()

		return np.array(r), np.array(g), np.array(b)