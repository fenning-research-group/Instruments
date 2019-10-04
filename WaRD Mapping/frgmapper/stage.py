import thorlabs_apt as apt
import time

class stage(object):

	def __init__(self, xMotorAddress = 45992790, yMotorAddress = 45951900):
		self.x = apt.Motor(xMotorAddress)
		self.y = apt.Motor(yMotorAddress)
		self.position = (self.x.position, self.y.position)

		self.x.enable()
		self.y.enable()

		if self.x.has_homing_been_completed and self.y.has_homing_been_completed:
			self.__homed = True
		else:
			self.__homed = False

	def premove(self):
		if self.__homed == False:
			print('Please home the stage first with .gohome()')
			return False

		return True

	def postmove(self):
		self.position = (self.x.position, self.y.position)

	def gohome(self):
		# self.x.set_move_home_parameters(self.x.get_move_home_parameters())
		# self.y.set_move_home_parameters(self.y.get_move_home_parameters())
		# self.x.set_velocity_parameters(self.x.get_velocity_parameters())
		# self.y.set_velocity_parameters(self.y.get_velocity_parameters())
		self.x.move_home(True)
		self.y.move_home(True)
		self.__homed = True

		self.postmove()
		return True

	def movetocenter(self):
		if not self.premove():
			return False
		
		self.moveto(x = 77, y = 97) 	#position where sample is roughly centered on int sphere port 2019-09-19

		self.postmove()
		return True

	def movetosampleloading(self):
		if not self.premove():
			return False
		
		self.moveto(x = 0, y = 150) 	#position where sample can be easily loaded 2019-08-13
		
		self.postmove()
		return True

		
	def enable(self):
		self.x.enable()
		self.y.enable()

	def disable(self):
		self.x.disable()
		self.y.disable()

	def moveto(self, x = None, y = None):
		if not self.premove():
			return False

		if x is not None:
			self.x.move_to(x)
		if y is not None:
			self.y.move_to(y)
		while not (not self.x.is_in_motion and not self.y.is_in_motion):
			time.sleep(0.1)

		self.postmove()
		return True

	def moverel(self, x = None, y = None):
		if not self.premove():
			return False

		if x:
			self.x.move_by(x)
		if y:
			self.y.move_by(y)
		while not (not self.x.is_in_motion and not self.y.is_in_motion):
			time.sleep(0.1)

		self.postmove()
		return True

