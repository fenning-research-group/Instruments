import thorlabs_apt as thorlabs_apt
import time

class stage():

	def __init__(xMotorAddress = '', yMotorAddress = ''):
		self.x = apt.Motor(xMotorAddress)
		self.y = apt.Motor(yMotorAddress)
		self.position = {'x': None, 'y': None}

		self.x.enable()
		self.y.enable()

		if self.x.has_homing_been_completed() and self.y.has_homing_been_completed():
			self.__homed = True
		else:
			self.__homed = False

	def premove(self):
		if self.__homed = False:
			print('Please home the stage first with .gohome()')
			return False

	def postmove(self):
		self.position['x'] = self.x.position
		self.position['y'] = self.y.position

	def gohome(self):
		self.x.movehome(True)
		self.y.movehome(True)
		self.__homed = True

		self.postmove()

	def enable(self):
		self.x.enable()
		self.y.enable()

	def disable(self):
		self.x.disable()
		self.y.disable()

	def moveto(x = None, y = None):
		if x:
			self.x.move_to(x)
		if y:
			self.y.move_to(y)
		while not (self.x.is_settled() and self.y.is_settled()):
			time.sleep(0.1)

		self.postmove()


	def moverel(x = None, y = None):
		if x:
			self.x.move_by(x)
		if y:
			self.y.move_by(y)
		while not (self.x.is_settled() and self.y.is_settled()):
			time.sleep(0.1)

		self.postmove()

