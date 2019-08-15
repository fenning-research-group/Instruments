import numpy as np
import matplotlib as plt
import os
import serial
import time

class control:

	def __init__(self, 
		flirport = 'COM4',
		kepcoport = 'COM5',
		laserport = 'COM1',
		dataqport = 'COM2'):

		# hardware properties
		self.flirport = flirport
		self.kepcoport = kepcoport
		self.laserport = laserport
		self.dataqport = dataqport
		self.__maxlasercurrent = 55000	#max current allowed by OSTech laser
		self.__laserON = False
		self.__kepcoON = False
		self.__flirON = False

		# measurement settings
		self._kepcomode = 'VOLT'
		self._bias = 0			#bias applied to sample
		self._lasercurrent = 0	#current supplied to laser ###may replace this with n_suns, if calibration is enabled
		self._saturationtime = 0.5	#delay between applying voltage/illumination and beginning measurement
		self._numIV = 10		#number of IV measurements to average
		self._numframes = 50	#number of image frames to average

	def connect(self):
		### connect to flir camera
		self.__flir = None

		# connect to kepco
		maxkepcocurrent = 3 	#max current in amps

		self.__kepco = serial.Serial(self.kepcoport)
		self.__kepco.open()
		self.__kepco.write(b'SYST:REM ON') #switch kepco to remote control - front panel will be made inactive
		self.__kepco.write(b'VOLT:RANG 1') #tell kepco to allow full voltage range (-20 to 20 V). Set this to "4" to change max range from -20 to 20 to -5 to 5
		self.__kepco.write(b'FUNC:MODE VOLT')   #set output mode to voltage
        self.__kepco.write(b('CURR ' + str(maxkepcocurrent))) #set maximum current threshold
		
		# Connect to OSTECH Laser
        max_laser_current = 55000 #mA

        self.__laser = serial.Serial(self.laserport)
        ### may need to change terminator to 'CR' somehow
        self.__laser.open()
        laserwrite(self.__laser, 'LCT 0.0')	#initialize laser to 0 current

        ### connect to the dataq

    def laserwrite(laser, writestr):
		# sends a command to the OSTech laser. The OSTech sends two responses by default - first, echos back original command, then says something command-specific. This helper clears the OSTech output buffer automatically
    	laser.write(writestr)
		tempstr = laser.readline()
		if tempstr is not writestr:
			print('Error: laser did not echo intended command.')
		tempstr = laser.readline()

		return tempstr

	def cleankepcostring(string):

	def preview(self):
		### function to preview the flir camera, used for sample alignment
		return None

	def setmeas(self,
		kepcomode = self._kepcomode,
		bias = self._bias,
		lasercurrent = self._lasercurrent,
		saturationtime = self._saturationtime,
		numIV = self._numIV,
		numframes = self._numframes):

		if kepcomode in ['I', 'CURR', 'OC', 'Open Circuit', 'opencircuit']:
			self._kepcomode = b'CURR'
		elif kepcomode in ['V', 'VOLT', 'SC', 'Short Circuit', 'shortcircuit']:
			self._kepcomode = b'VOLT'
		self.__kepco.write(b'FUNC:MODE ' + self._kepcomode)

		if self._kepcomode is b'CURR':
			self._bias = 0
			if bias is not 0:
				print('Cannot apply voltage bias while kepco is set to CURR mode: bias has been automatically adjusted from {0:d} to 0'.format(bias))
		else:
			self._bias = bias
		self.__kepco.write(b'VOLT {0:d}'.format(self._bias))

		if lasercurrent > self.__maxlasercurrent:
			self._lasercurrent = self.__maxlasercurrent
			print('Invalid laser current, too high: corrected from {0:d} to {1:d}'.format(lasercurrent, self.__maxlasercurrent))
		elif lasercurrent < 0:
			self._lasercurrent = 0
			print('Invalid laser current, too low: corrected from {0:d} to 0'.format(lasercurrent))
		else:
			self._lasercurrent = lasercurrent
		laserwrite(self.__laser, b'{0:d}.0'.format(self._lasercurrent))

		self._numIV = numIV
		self._numframes = numframes

	def takemeas(self, lastmeasurement = True):
		if not self.__laserON and self._lasercurrent > 0:
			laserwrite(self.__laser, 'LR')	#turn on the laser (Laser Run)
			self.__laserON = True
		if not self.__kepcoON and self._kepcomode is 'VOLT' and self._bias is not 0:
			self.__kepco.write('OUTP ON')	#turn on the kepco source
			self.__kepcoON == True

		time.sleep(self._saturationtime)

		#take image, take IV meas during image

		if self.__laserON and lastmeasurement:
			laserwrite(self.__laser, 'LS')
			self.__laserON = False
		if self.__kepcoON and lastmeasurement:
			self.__kepco.write('OUTP OFF')	#turn off the kepco source
			self.__kepcoON = False

	def takeimage(self):
		###do some flir stuff here
		return None

	# def takePL(self, lasercurrent, numframes = 100, saturationtime = 0.5):

	# 	#self.__kepco.write(b'CURR 0') #set kepco current to 0
	# 	self.__kepco.write(b'FUNC:MODE CURR')	#set kepco to current mode, this holds current at 0 and keeps cell at open circuit even when the leads are connected to the kepco
		
	# 	###set up flir recording here
	# 	dat = []

	# 	laserwrite(self.__laser, 'LR')	#turn on the laser (Laser Run)
	# 	for curr in lasercurrent:
	# 		writestr = 'LCT ' + str(curr) + '.0'
	# 		laserwrite(self.__laser, writestr)	#set laser current
	# 		time.sleep(saturationtime)
	# 		dat.append(takeimage()) #take the image here

	# 	laserwrite(self.__laser, 'LS')	#turn off the laser (Laser Stop)
	# 	laserwrite(self.__laser, 'LCT 0.0')	#set laser current back to 0
	# 	self.__kepco.write(b'FUNC:MODE VOLT')	#set kepco to current mode, this holds current at 0 and keeps cell at open circuit even when the leads are connected to the kepco

	# 	return dat

	# def takeEL(self, voltage, numframes = 100, numIVmeasurements = 10, saturationtime = 0.5):

	# 	return dat

	# def takePLIV(self, voltage, lasercurrent, numframes = 100, lasersaturationtime = 0.5):

	# 	#self.__kepco.write(b'CURR 0') #set kepco current to 0
	# 	self.__kepco.write(b'FUNC:MODE CURR')	#set kepco to current mode, this holds current at 0 and keeps cell at open circuit even when the leads are connected to the kepco
		
	# 	#set up flir recording here
	# 	dat = []

	# 	laserwrite(self.__laser, 'LR')	#turn on the laser (Laser Run)
	# 	for curr in lasercurrent:
	# 		writestr = 'LCT ' + str(curr) + '.0'
	# 		laserwrite(self.__laser, writestr)	#set laser current
	# 		time.sleep(lasersaturationtime)
	# 		dat.append(takeimage()) #take the image here

	# 	laserwrite(self.__laser, 'LS')	#turn off the laser (Laser Stop)
	# 	laserwrite(self.__laser, 'LCT 0.0')	#set laser current back to 0

	# 	return dat




