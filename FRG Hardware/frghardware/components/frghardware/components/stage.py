import time
import threading
try:
	import thorlabs_apt as apt
except:
	print('Thorlabs APT did not load properly - if needed, ensure that DLL has been installed!')
class Thorlabs_LTS150_xy(object):

	def __init__(self, xMotorAddress = 45992790, yMotorAddress = 45951900):
		self.x = self.apt.Motor(xMotorAddress)
		self.y = self.apt.Motor(yMotorAddress)
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
		def goHomeThread(motor):
			foundHome = False
			maxAttempts = 3
			attempts = 0

			while (attempts < maxAttempts) and not foundHome:
				try:
					motor.move_home(True)
				except:
					attempts = attempts + 1
				if motor.has_homing_been_completed:
					foundHome = True

			return foundHome
			
		xThread = threading.Thread(target = goHomeThread, args = (self.x,))
		yThread = threading.Thread(target = goHomeThread, args = (self.y,))
		xThread.start()
		yThread.start()
		xThread.join()
		yThread.join()


		xHomed = self.x.has_homing_been_completed
		yHomed = self.y.has_homing_been_completed
		if xHomed and yHomed:
			self.__homed = True
		else:
			self.__homed = False
			errorstr = 'Error encounted: '
			if not xHomed:
				errorstr += 'x'
			if not yHomed:
				errorstr += 'y'
			errorstr += ' did not successfully find home.'
			print(errorstr)

		self.postmove()
		return self.__homed

	def movetocenter(self):
		if not self.premove():
			return False
		
		self.moveto(x = 68.5, y = 97.5) 	#position where sample is roughly centered on int sphere port 2019-10-14

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


class PLStage:
	def __init__(self, sampleposition = (523.61, 41.000), port = 'COM8'):
		self.__xlim = (0.500, 205.500)
		self.__ylim = (0.500, 194.500)
		self.position = (None, None)
		self.connect(port = port)	
		self._homed = False
		self.samplePosition = sampleposition

	def connect(self, port = 'COM8'):
		self.__handle = serial.Serial(port)
		return True

	def disconnect(self):
		self.__handle.close()
		return True

	def premove(self, x, y):
		if self._homed == False:
			print('Please home the stage first with .gohome()')
			return False
	
		#make sure coordinates are allowed by stage dimensions
		if (x < self.__xlim[0]) or (x > self.__xlim[1]):
			return False
		if (y < self.__ylim[0]) or (y > self.__ylim[1]):
			return False

		return True

	def postmove(self, x, y):
		self.position = (x, y)

	def gohome(self):
		self.__handle.write('1/1/'.encode())	#go home in x
		self.waitforstage()
		self.__handle.write('1/2/'.encode()) #go home in y
		self.waitforstage()

		self._homed = True
		self.postmove(0, 0)

		return True

	def movetosample(self):
		x = self.samplePosition[0]
		y = self.samplePosition[1]

		if not self.premove(x = x, y = y):
			return False
		
		self.moveto(x = x, y = y) 	#position where sample is roughly centered on int sphere port 2019-08-13

		return True

	# def gotodetector(self):
	# 	x = self.samplePosition[0]+self.__detectorOffset[0]
	# 	y = self.samplePosition[1]+self.__detectorOffset[1]

	# 	if not self.premove(x = x, y = y):
	# 		return False
		
	# 	self.moveto(x = x, y = y) 	#position where Si photodetector is in center of camera FOV

		return True

	def moveto(self, x = None, y = None):
		if not x:
			x = self.position[0]

		if not y:
			y = self.position[1]

		if not self.premove(x = x, y = y):
			return False

		if x is not self.position[0]:
			self.__handle.write('4/1/{0:d}/'.format(x*1000).encode()) #stage controller works in um, not mm!
			self.waitforstage()
		if y is not self.position[1]:
			self.__handle.write('4/2/{0:d}/'.format(y*1000).encode()) #stage controller works in um, not mm!
			self.waitforstage()

		self.postmove(x, y)
		return True

	def moverel(self, x = 0, y = 0):
		if not self.premove(x = self.position[0] + x, y = self.position[1] + y):
			return False

		if x:
			self.__handle.write('2/1/{0:d}/'.format(x*1000).encode()) #stage controller works in um, not mm!
			self.waitforstage()
		if y:
			self.__handle.write('2/2/{0:d}/'.format(y*1000).encode()) #stage controller works in um, not mm!
			self.waitforstage()

		self.postmove(self.position[0] + x, self.position[1] + y)
		return True

	def waitforstage(self):
		#method to pause until the stage has finished moving.
		moving = False

		while not moving:
			while self.__handle.in_waiting > 0:
				update = self.__handle.readline()

				if update == (str(91) + '\n').encode():	#message saying axis 1 has begun moving
					update = self.__handle.readline()
					if update == ('1\n').encode():
						axis = 1
						moving = True
						break
				if update == (str(92) + '\n').encode(): #message saying axis 2 has begun moving
					update = self.__handle.readline()
					if update == ('1\n').encode():
						axis = 2
						moving = True
						break
				if update == (str(52) + '\n').encode():
					print('Error flagged by arduino, movement not executed')
					return
			time.sleep(1)

		# print('Moving!')

		while moving:
			while self.__handle.in_waiting > 0:
				update = self.__handle.readline()
				# print(update)
				if update == (str(90 + axis) + '\n').encode():	#message saying that axis which had previously begun moving has now stopped moving
					update = self.__handle.readline()
					if update == ('0\n').encode():
						moving = False
						break
			time.sleep(1)


	def stagegui(self):
		ser = self.__handle
		import serial
		import tkinter
		import sys
		import glob
		import numpy

		def send_msg(list, ser):
			msg = '';
			for each in list:
				msg = msg + str(each) + '/'

			ser.write(msg[:-1].encode())
			print(msg[:-1])

		def send_move_msg(list, entryobj, ser):
			targetpos = entryobj.get()
			if targetpos:
				targetpos = int(targetpos)
				if len(list) == 2:
						list.append(targetpos)
				else:
					list[2] = targetpos
				send_msg(list, ser)

		def getports():
			""" Lists serial port names

				:raises EnvironmentError:
					On unsupported or unknown platforms
				:returns:
					A list of the serial ports available on the system
			"""
			if sys.platform.startswith('win'):
				ports = ['COM%s' % (i + 1) for i in range(256)]
			elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
				# this excludes your current terminal "/dev/tty"
				ports = glob.glob('/dev/tty[A-Za-z]*')
			elif sys.platform.startswith('darwin'):
				ports = glob.glob('/dev/tty.*')
			else:
				raise EnvironmentError('Unsupported platform')

			result = []
			for port in ports:
				try:
					s = serial.Serial(port)
					s.close()
					result.append(port)
				except (OSError, serial.SerialException):
					pass
			return result

		def select_COM():

			def cursor_select(evt):
				global com_port
				com_port = str((comlist.get(comlist.curselection())))
				top.destroy()

			available_ports = getports()

			top = tkinter.Tk()
			comlist = tkinter.Listbox(top)
			for portidx, port in enumerate(available_ports):
				comlist.insert(portidx, port)

			comlist.pack()
			comlist.bind('<<ListboxSelect>>', lambda arg1 = comlist: cursor_select(arg1))

			top.mainloop()

			return(com_port)


		def main():
			status = [0,0,0,0,0,0,0,0,0,0]
			msgbox = [0,0,0,0,0,0,0,0,0,0]
					# updates = {
					# 11: 0#'encoder_count_x',
					# 21: 1#'last_encoded_position_x',
					# 31: 2#'currentpos_x',
					# 41: 3#'targetpos_x',
					# 91: 4#'moving_x',
					# 12: 5#'encoder_count_y',
					# 22: 6#'last_encoded_position_y',
					# 32: 7#'currentpos_y',
					# 42: 8#'targetpos_y',
					# 92: 9#'moving_y'

			def closeprogram(ser,top):
				# ser.write(b'0')
				# ser.close()
				top.destroy()

			# ser = serial.Serial()
			# ser.baudrate = 9600
			# ser.port = select_COM()

			# # if not ser.is_open:
			# ser.open()

			top = tkinter.Tk()
			tkinter.Label(top, text = "Current X Position").grid(row = 0, column = 0)
			tkinter.Label(top, text = "Current Y Position").grid(row = 0, column = 1)

			msgbox[2] = tkinter.Message(top, text = str(status[2]) + ' um')
			msgbox[2].grid(row = 1, column = 0)
			msgbox[7] = tkinter.Message(top, text = str(status[7]) + ' um')
			msgbox[7].grid(row = 1, column = 1)

			tkinter.Label(top, text = "Target X Position").grid(row = 2, column = 0)
			tkinter.Label(top, text = "Target Y Position").grid(row = 2, column = 1)

			targetpos_x_input = tkinter.Entry(top)
			targetpos_x_input.grid(row = 3, column = 0)
			targetpos_y_input = tkinter.Entry(top)
			targetpos_y_input.grid(row = 3, column = 1)

			move_x = tkinter.Button(top, text = 'Move to Target X')
			move_x['command'] = lambda arg1 = [4,1], arg2 = targetpos_x_input, arg3 = ser: send_move_msg(arg1,arg2,arg3)
			move_x.grid(row = 4, column = 0)

			move_y = tkinter.Button(top, text = 'Move to Target Y')
			move_y['command'] = lambda arg1 = [4,2], arg2 = targetpos_y_input, arg3 = ser: send_move_msg(arg1,arg2,arg3)
			move_y.grid(row = 4, column = 1)

			relpos_x_input = tkinter.Entry(top)
			relpos_x_input.grid(row = 5, column = 0)
			relpos_y_input = tkinter.Entry(top)
			relpos_y_input.grid(row = 5, column = 1)

			relmove_x = tkinter.Button(top, text = 'Move Relative X')
			relmove_x['command'] = lambda arg1 = [2,1], arg2 = relpos_x_input, arg3 = ser: send_move_msg(arg1,arg2,arg3)
			relmove_x.grid(row = 6, column = 0)

			relmove_y = tkinter.Button(top, text = 'Move Relative Y')
			relmove_y['command'] = lambda arg1 = [2,2], arg2 = relpos_y_input, arg3 = ser: send_move_msg(arg1,arg2,arg3)
			relmove_y.grid(row = 6, column = 1)  

			gohome_x = tkinter.Button(top, text = 'Find X Home')
			gohome_x['command'] = lambda arg1 = [1,1], arg2 = ser : send_msg(arg1,arg2)
			gohome_x.grid(row = 7, column = 0)

			gohome_y = tkinter.Button(top, text = 'Find Y Home')
			gohome_y['command'] = lambda arg1 = [1,2], arg2 = ser : send_msg(arg1,arg2)
			gohome_y.grid(row = 7, column = 1)

			# openmapgui_button = tkinter.Button(top, text = 'Area Map')
			# openmapgui_button['command'] = print(1)
			# openmapgui_button.grid(row = 8, column = 0)


			tkinter.Label(top, text = 'Encoder Count X:').grid(row = 0, column = 2)
			msgbox[0] = tkinter.Message(top, text = str(status[0]))
			msgbox[0].grid(row = 0, column = 3)
			tkinter.Label(top, text = 'Last Encoded Position X:').grid(row = 1, column = 2)
			msgbox[1] = tkinter.Message(top, text = str(status[1]))
			msgbox[1].grid(row = 1, column = 3)
			tkinter.Label(top, text = 'Controller Target X:').grid(row = 2, column = 2)
			msgbox[3] = tkinter.Message(top, text = str(status[3]))
			msgbox[3].grid(row = 2, column = 3)
			tkinter.Label(top, text = 'X Moving:').grid(row = 3, column = 2)
			msgbox[4] = tkinter.Message(top, text = str(status[4]))
			msgbox[4].grid(row = 3, column = 3)

			tkinter.Label(top, text = 'Encoder Count Y:').grid(row = 4, column = 2)
			msgbox[5] = tkinter.Message(top, text = str(status[5]))
			msgbox[5].grid(row = 4, column = 3)
			tkinter.Label(top, text = 'Last Encoded Position Y:').grid(row = 5, column = 2)
			msgbox[6] = tkinter.Message(top, text = str(status[6]))
			msgbox[6].grid(row = 5, column = 3)
			tkinter.Label(top, text = 'Controller Target Y:').grid(row = 6, column = 2)
			msgbox[8] = tkinter.Message(top, text = str(status[8]))
			msgbox[8].grid(row = 6, column = 3)
			tkinter.Label(top, text = 'Y Moving:').grid(row = 7, column = 2)
			msgbox[9] = tkinter.Message(top, text = str(status[9]))
			msgbox[9].grid(row = 7, column = 3)
			top.protocol("WM_DELETE_WINDOW", lambda arg1 = ser, arg2 = top : closeprogram(arg1,arg2))

			def check_for_updates():
				if ser.inWaiting():
					reading = True
		#			currentval = 0
					totalvals = []
					while reading:
		#				new_val = ser.read()
		#				print(new_val)
		#				if new_val != b',':
		#					if new_val == b'S':
		#						reading = False
		#					else:
		#						new_val = int(new_val)
		#						currentval = currentval*10 + new_val
		#				else:
		#					if reading:
		#						totalvals.append(currentval)
		#						currentval = 0
						new_val = ser.readline()
						if new_val == b'S\n':
							reading = False
						else:
							totalvals.append(float(new_val[:-1]))
					# print(totalvals)
					parse_update(totalvals)
					
				top.after(100, check_for_updates)

			def parse_update(vals):
				updates = {
					11: 0,#'encoder_count_x',
					21: 1,#'last_encoded_position_x',
					31: 2,#'currentpos_x',
					41: 3,#'targetpos_x',
					91: 4,#'moving_x',
					12: 5,#'encoder_count_y',
					22: 6,#'last_encoded_position_y',
					32: 7,#'currentpos_y',
					42: 8,#'targetpos_y',
					92: 9#'moving_y'
				}

				for idx in range(int(len(vals)/2)):
		                        if vals[2*(idx-1)] in updates:
		                                status[updates[vals[2*(idx-1)]]] = vals[2*(idx-1)+1]

				for idx in range(len(status)):
					msgbox[idx].config(text = str(status[idx]))

			top.after(100, check_for_updates)
			top.mainloop()

		### Function Start ###
		main()

