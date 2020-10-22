import pyvisa
import time

class Mono(object):

	def __init__(self, monoAddress = 'GPIB0::4::INSTR'):
		self.pauseTime = 0.015	#time to pause between subsequent communication to mono, in seconds. set to 10 ms on 2019-09-10
		#self.handle = pyvisa.ResourceManager().open_resource(monoAddress)
		if self.connect(monoAddress = monoAddress):
			# self.handle.write('OUTPORT 1')	#select output port (1 = inline, 2 = axial)
			self.currentWavelength = float(self.handle.query('WAVE?'))
			self.currentFilter = int(self.handle.query('FILTER?'))
			self.currentGrating = int(self.handle.query('GRAT?')[0])

		self.wavelengthTolerance = 0.1 #nm

		self.shutterOpenStatus = None
		self.close_shutter()

	@property
	def wavelength(self):
		self.__wavelength = float(self.handle.query('WAVE?'))
		return self.__wavelength
	@wavelength.setter
	def wavelength(self, wl):
		self.goToWavelength(wl)
	
	def connect(self, monoAddress):
		self.handle = pyvisa.ResourceManager().open_resource(monoAddress)
		self.handle.timeout=10000 # set timeout to 10 s (input value in ms)
		time.sleep(self.pauseTime)
		self.handle.read_termination = '\r\n'
		self.handle.write_termination = '\r\n'
		return True

	def disconnect(self):
		self.handle.close()	#not sure if this line works
		return True

	def open_shutter(self):
		if not self.shutterOpenStatus:
			self.handle.write('SHUTTER O')
		self.shutterOpenStatus = True
		return True

	def close_shutter(self):
		if self.shutterOpenStatus:
			self.handle.write('SHUTTER C')
		self.shutterOpenStatus = False
		return True

	def select_port(self, port):
		if port in [1, 'inline']:
			self.handle.write('OUTPORT 1')	#select output port (1 = inline, 2 = axial)
		elif port in [2, 'axial']:
			self.handle.write('OUTPORT 2')
		else:
			raise Exception('Invalid port selected - valid inputs are "inline" or "axial"')
		return True

	def goToWavelength(self, targetWavelength):
		#check to see if we even need to change wavelengths - if we are already at target, don't waste time on further communication with mono
		if (abs(self.wavelength - targetWavelength) < self.wavelengthTolerance):
			return True

		if targetWavelength < 350: # No filter
			time.sleep(self.pauseTime)
			self.handle.write('FILTER 4')
			targetFilter = 4

		elif targetWavelength < 600: # 335 nm Filter
			time.sleep(self.pauseTime)
			self.handle.write('FILTER 1')
			targetFilter = 1

		elif targetWavelength < 1010: # 590 nm Filter
			time.sleep(self.pauseTime)
			self.handle.write('FILTER 2')
			targetFilter = 2

		elif targetWavelength <= 2000:
			time.sleep(self.pauseTime)
			targetFilter = 3
			self.handle.write('FILTER 3') # 1000 nm Filte
		
		else:
			time.sleep(self.pauseTime)
			self.handle.write( 'FILTER 4') # no filter
			targetFilter = 4

		#Conditions for grating change
		if targetWavelength < 700:
			time.sleep(self.pauseTime)
			self.handle.write('GRAT 1')
			targetGrating = 1

		else:
			time.sleep(self.pauseTime)
			self.handle.write('GRAT 2')
			targetGrating = 2



		time.sleep(self.pauseTime)
		self.handle.write('GOWAVE {0:.2f}'.format(targetWavelength)) #reads Ch1

		#Wait for changes
		waitingForMonoMove = True
		timer = 0
		while waitingForMonoMove:
			time.sleep(self.pauseTime)
			self.currentFilter = int(self.handle.query('FILTER?'))
			self.currentGrating = int(self.handle.query('GRAT?')[0])

			if (abs(self.wavelength-targetWavelength)<self.wavelengthTolerance) and (self.currentFilter==targetFilter) and (self.currentGrating==targetGrating):
				waitingForMonoMove = False

			timer = timer + 1
			if timer > (30/self.pauseTime): #equivalent to 300 seconds
				print('MonoMoveError')
				return False

		return True