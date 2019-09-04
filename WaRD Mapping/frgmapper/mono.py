import pyvisa
import time

class mono(object):

	def __init__(self, monoAddress = 'GPIB0::4::INSTR'):
		self.pauseTime = 0.1
		#self.handle = pyvisa.ResourceManager().open_resource(monoAddress)
		self.handle = pyvisa.ResourceManager().open_resource(monoAddress)
		self.handle.timeout=10000 # set timeout to 10 s
		time.sleep(self.pauseTime)
		self.handle.read_termination = '\r\n'
		self.handle.write_termination = '\r\n'
		self.handle.write('OUTPORT 1')	#select output port (1 = inline, 2 = axial)
		self.currentWavelength = float(self.handle.query('WAVE?'))
		self.currentFilter = int(self.handle.query('FILTER?'))
		self.currentGrating = int(self.handle.query('GRAT?')[0])

		self.wavelengthTolerance = 2 #nm
		self.shutterOpenStatus = False

	def openShutter(self):
		if not self.shutterOpenStatus:
			self.handle.write('SHUTTER O')
		self.shutterOpenStatus = True

	def closeShutter(self):
		if self.shutterOpenStatus:
			self.handle.write('SHUTTER C')
		self.shutterOpenStatus = False
		
	def goToWavelength(self, targetWavelength):

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
		self.handle.write('GOWAVE {0:d}'.format(targetWavelength)) #reads Ch1

		#Wait for changes
		waitingForMonoMove = True
		timer = 0
		while waitingForMonoMove:
			time.sleep(self.pauseTime)
			self.currentWavelength = float(self.handle.query('WAVE?'))
			self.currentFilter = int(self.handle.query('FILTER?'))
			self.currentGrating = int(self.handle.query('GRAT?')[0])

			if (abs(self.currentWavelength-targetWavelength)<self.wavelengthTolerance) and (self.currentFilter==targetFilter) and (self.currentGrating==targetGrating):
				waitingForMonoMove = False

			timer = timer + 1
			if timer > (30/self.pauseTime): #equivalent to 300 seconds
				print('MonoMoveError')
				return False

		return True