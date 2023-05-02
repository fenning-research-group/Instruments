import serial
import time
import numpy as np
import pandas as pd
# import struct


class Stepper:

    def __init__(self, port):

        self.port = port
        self.POLLINGDELAY = 0.02
        self.HOMINGTIME = 5
        self.connect()

    def connect(self):

    	try:
        	self.arduino = serial.Serial(port = self.port, baudrate =  9600)
        except:
        	print("Unplug Arduino and try again!")

    def gohome(self):

    	self.arduino.close()
    	sleep(2)
    	self.connect()
    	sleep(self.HOMINGTIME)

    def moveto(self, position):

    	arduino.write(str(position).encode())

	    while arduino.in_waiting == 0:
	        pass

	    sleep(0.01)
	    num = arduino.in_waiting
	    string = arduino.read(num).decode('utf-8')
	    print(f'Moved to {string}')