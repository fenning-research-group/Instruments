import visa
import time

class mono():

	def __init__(monoAddress = ''):
		self.handle = visa.ResourceManager().open_resource(monoAddress)
		self.currentWavelength = float(self.handle.query('WAVE?'))
		self.currentFilter = int(self.handle.query('FILTER?'))
		self.currentGrating = int(self.handle.query('GRAT?'))
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
		
	def goToWavelength(self, wavelength):
		pauseTime= 0.1

		if targetWavelength < 350: # No filter
			time.sleep(pauseTime)
			monoHandle.write('FILTER 4')
			targetFilter = 4

		elif targetWavelength < 600: # 335 nm Filter
			time.sleep(pauseTime)
			monoHandle.write('FILTER 1')
			targetFilter = 1

		elif targetWavelength < 1010: # 590 nm Filter
			time.sleep(pauseTime)
			monoHandle.write('FILTER 2')
			targetFilter = 2

		elif targetWavelength <= 2000:
			time.sleep(pauseTime)
			targetFilter = 3
			monoHandle.write('FILTER 3') # 1000 nm Filte
		
		else:
			time.sleep(pauseTime)
			monoHandle.write( 'FILTER 4') # no filter
			targetFilter = 4

		#Conditions for grating change
		if targetWavelength < 700:
			time.sleep(pauseTime)
			monoHandle.write('GRAT 1')
			targetGrating = 1

		else:
			time.sleep(pauseTime)
			monoHandle.write('GRAT 2')
			targetGrating = 2



		time.sleep(pauseTime)
		monoHandle.query('GOWAVE {0:d}'.format(targetWavelength)) #reads Ch1
		time.sleep(pauseTime)

		#Wait for changes
		waitingForMonoMove = True
		timer = 0
		while waitingForMonoMove:
			time.sleep(pauseTime)
			self.currentWavelength = float(monoHandle.query('WAVE?'))
			self.currentFilter = int(monoHandle.query('FILTER?'))
			self.currentGrating = int(monoHandle.query('GRAT?'))

			if (abs(self.currentWavelength-targetWavelength)<self.wavelengthTol) and (self.currentFilter==targetFilter) and (self.currentGrating==targetGrating):
				waitingForMonoMove = False

			timer = timer + 1
			if timer > 30:
				print('MonoMoveError')
				return False

		return True