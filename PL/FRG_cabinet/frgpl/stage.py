## module for communication with OSTech laser controller

import serial

class stage(object):
	def __init__(self, port = 'COM11'):
		self.__xlim = (500, 205500)
		self.__ylim = (500, 194500)
		self.position = (None, None)
		self.connect(port = port)	
		self.samplePosition = (None, None)	#stage coordinates where sample is in camera FOV. might move to parent class
		self.__detectorOffset = (None, None)	# offset between sample center and photodetector. might move to parent class
		self.__homed = False

	def connect(self, port = 'COM11'):
		self.__handle = serial.Serial(port)
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def premove(self, x, y):
		if self.__homed == False:
			print('Please home the stage first with .gohome()')
			return False
	
		#make sure coordinates are allowed by stage dimensions
		if (x < self.__xlim[0]) or (x > self.__xlim[1]):
			return False
		if (y < self.__ylim[0]) or (y > self.__ylim[1]):
			return False

		return True

	def postmove(self):
		self.position = (self.x.position, self.y.position)

	def gohome(self):
		self.__handle.write('1/1/')	#go home in x
		self.waitforstage()
		self.__handle.write('1/2/') #go home in y
		self.waitforstage()

		self.__homed = True
		self.postmove()

		return True

	def gotosample(self):
		if not self.premove():
			return False
		
		self.moveto(x = self.samplePosition[0], y = self.samplePosition[1]) 	#position where sample is roughly centered on int sphere port 2019-08-13

		return True

	def gotodetector(self):
		if not self.premove():
			return False
		
		self.moveto(x = self.samplePosition[0]+self.__detectorOffset[0], y = self.samplePosition[1]+self.__detectorOffset[1]) 	#position where Si photodetector is in center of camera FOV

		return True

		
	def moveto(self, x = position[0], y = position[1]):
		if not self.premove(x = x, y = y):
			return False

		if x is not self.position[0]:

			self.waitforstage()
		if y is not self.position[1]:

			self.waitforstage()


		self.postmove()
		return True

	def moverel(self, x = 0, y = 0):
		if not self.premove(x = self.position[0] + x, y = self.position[1] + y):
			return False

		if x:

			self.waitforstage()

		if y:
			self.waitforstage()

		self.postmove()
		return True