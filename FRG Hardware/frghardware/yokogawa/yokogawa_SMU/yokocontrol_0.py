# to run in terminal:
# 1. cd "C:\Users\dcaka\Documents\GitHub\Instruments\FRG Hardware\frghardware\keithleyjv\frghardware\keithleyjv"
# 2. from frghardware.keithleyjv import yokocontrol1
# 3. c = yokocontrol1.Control()

# for fast iteration on the code you can load:
# 1. import importlib
# 2. importlib.reload(yokocontrol1)


import pyvisa
import pandas as pd
import serial
import time
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import style
mpl.rcParams.update(mpl.rcParamsDefault)

# General Control Class for Yokogawa JV
class Control:
	def __init__(self):
		self.delay = 0.05
		# self.counts = 2 
		self.__previewFigure = None
		self.__previewAxes = None
		self.connect()

	# Connect to yoko
	def connect(self, yoko_address = 'GPIB0::1::INSTR'):
		rm = pyvisa.ResourceManager()
		self.yoko = rm.open_resource(yoko_address)
		self.yoko.timeout = 1000000 

	# Turn measurment on: Init settings for source V, measure I
	def jv_settings_0(self):
		self.yoko.write('*RST') # Reset Factory
		self.yoko.write(':SOUR:FUNC VOLT') # Source function Voltage
		self.yoko.write(':SOUR:VOLT:RANG 1V') # Source range setting 1 V
		self.yoko.write(':SOUR:CURR:PROT:LINK ON') # Limiter tracking ON
		self.yoko.write(':SOUR:CURR:PROT:ULIM 50mA') # Limiter 50 mA
		self.yoko.write(':SOUR:CURR:PROT:STAT ON') # Limiter ON
		self.yoko.write(':SOUR:VOLT:LEV 0V') # Source level 0 VOLT
		self.yoko.write(':SENS:STAT ON') # Measurement ON
		self.yoko.write(':SENS:FUNC CURR') # Measurement function Current
		self.yoko.write(':SENS:ITIM MIN') # Integration time Minimum
		self.yoko.write(':SENS:AZER:STAT OFF') # Auto zero OFF
		self.yoko.write(':TRIG:SOUR EXT') # Trigger source External trigger
		self.yoko.write(':SOUR:DEL MIN') # Source delay Minimum
		tempdelay = ':SENS:DEL ' + str(self.delay) + ' ms'
		self.yoko.write(tempdelay) # Measure delay set in __init__
		self.yoko.write(':OUTP:STAT ON') # Output ON

	# Turn measurment on: Init settings for source I, measure V
	def voc_settings(self):
		self.yoko.write('*RST') # Reset Factory
		self.yoko.write(':SOUR:FUNC CURR') # Source function Current
		self.yoko.write(':SOUR:CURR:RANG 1A') # Source range setting 0 A		
		self.yoko.write(':SOUR:VOLT:PROT:LINK ON') # Limiter tracking ON
		self.yoko.write(':SOUR:VOLT:PROT:ULIM 2V') # Limiter 2 V
		self.yoko.write(':SOUR:VOLT:PROT:STAT ON') # Limiter ON
		self.yoko.write(':SOUR:CURR:LEV 0A') # Source level –1.5 VOLT
		self.yoko.write(':SENS:STAT ON') # Measurement ON
		self.yoko.write(':SENS:FUNC VOLT') # Measurement function Current
		self.yoko.write(':SENS:ITIM MIN') # Integration time Minimum
		self.yoko.write(':SENS:AZER:STAT OFF') # Auto zero OFF
		self.yoko.write(':TRIG:SOUR EXT') # Trigger source External trigger
		self.yoko.write(':SOUR:DEL MIN') # Source delay Minimum
		tempdelay = ':SENS:DEL ' + str(self.delay) + ' ms' # read delay from __init__
		self.yoko.write(tempdelay) # Measure delay as set above
		self.yoko.write(':OUTP:STAT ON') # Output ON


	# Turn output/measurment off
	def output_off(self): 
		self.yoko.write(':OUTP:STAT OFF')

	# Get output as string regardless of source/measure
	def TrigRead(self): 
		self.TrigReadAsString = self.yoko.query(':INIT;*TRG;:FETC?') # initializes, apllies trigger, fetches value
		self.TrigReadAsFloat = float(self.TrigReadAsString) # convert to Float 

	# Set Voltage
	def volt_command(self):
		tempstr = ':SOUR:VOLT:LEV ' + str(self.v_point) +'V' 
		self.yoko.write(tempstr)

	# Set Current
	def current_command(self):
		tempstr = ':SOUR:CURR:LEV ' + str(self.a_point) +'A'
		self.yoko.write(tempstr)

	# Calculate Voc --> returns None right now
	def voc(self):
		self.voc_settings()
		self.a_point = 0
		self.current_command()
		self.TrigRead()
		voc = self.TrigReadAsFloat
		return voc

	# Sweep from vmin to vmax with steps #steps using device area 3 cm^2
	def jv(self, name, vmin=-0.1,vmax=1,steps=500, reverse = True, area = 3, preview=True):
		# load JV settings
		self.jv_settings_0()

		# scans reverse first if scanning both rev and fwd
		if reverse:
			# create arrays to hold voltage and current
			v = np.linspace(vmax, vmin, steps) 
			i = np.zeros(steps) 

			# set voltage, measure current
			for idx, v_point in enumerate(v): # cycle through v array
				self.v_point = v_point # load v_point
				self.volt_command() # use volt_command to set voltage

				self.TrigRead() # read the output of the measured parameter 

				i[idx] = self.TrigReadAsFloat # set the value of current in i

			self.output_off() # turn off measurment

			# store data in data frame
			data = pd.DataFrame({
				    'voltage': v,
				    'current': i
				})

			# print data to csv
			data.to_csv(f'{name}_rev.csv')

			# preview data
			if preview:
				j = -1*i/area/.001
				self._preview(v, j, f'{name}_rev')

			# return pandas dataframe
			# return data_rev
			time.sleep(1)


		# load JV settings
		self.jv_settings_0()

		# create arrays to hold voltage and current
		v = np.linspace(vmin, vmax, steps) 
		i = np.zeros(steps) 

		# set voltage, measure current
		for idx, v_point in enumerate(v): # cycle through v array
			self.v_point = v_point # load v_point
			self.volt_command() # use volt_command to set voltage

			self.TrigRead() # read the output of the measured parameter 

			i[idx] = self.TrigReadAsFloat # set the value of current in i

		self.output_off() # turn off measurment

		# store data in dataframe
		data = pd.DataFrame({
			    'voltage': v,
			    'current': i
			})

		# print data to csv
		data.to_csv(f'{name}_fwd.csv') # could probably comnbine fwd and rev into 1 csv

		# preview sweeped data
		if preview:
			j = -1*i/area/.001
			self._preview(v, j, f'{name}_fwd')

		# return pandas dataframe
		# return data_fwd


	# Manages preview
	def _preview(self, v, j, label): #
		def handle_close(evt, self):
			self.__previewFigure = None
			self.__previewAxes = None
		if self.__previewFigure is None: #if preview window is not created yet, lets make it
			plt.ioff()
			self.__previewFigure, self.__previewAxes = plt.subplots()
			self.__previewFigure.canvas.mpl_connect('close_event', lambda x: handle_close(x, self))	# if preview figure is closed, lets clear the figure/axes handles so the next preview properly recreates the handles
			plt.ion()
			plt.xlim(np.min(v), np.max(v)+.1)
			plt.ylim(-5, np.max(j)+5)
			plt.ylabel('Current Density (mA/cm²)')
			plt.xlabel('Voltage (V)')
			plt.axhline(0, color='black', linestyle='--')
			plt.show()
		# for ax in self.__previewAxes:	#clear the axes
		# 	ax.clear()
		self.__previewAxes.plot(v,j, label=label) # plot data
		self.__previewAxes.legend()
		self.__previewFigure.canvas.draw() # draw plot
		self.__previewFigure.canvas.flush_events()
		time.sleep(1e-4) # pause to allow plot to update



# old stuff:

	# # Hardcode setup
	# def setup_slow_points(self):
	# 	self.yoko.write('*RST') #Reset Factory#
	# 	self.yoko.write(':SOUR:FUNC VOLT') # Source function Voltage
	# 	self.yoko.write(':SOUR:VOLT:RANG 2V') # Source range setting 2 V
	# 	self.yoko.write(':SOUR:CURR:PROT:LINK ON') # ‘ Limiter tracking ON
	# 	self.yoko.write(':SOUR:CURR:PROT:ULIM 2mA') #‘ Limiter 50 mA
	# 	self.yoko.write(':SOUR:CURR:PROT:STAT ON') # ‘ Limiter ON
	# 	self.yoko.write(':SOUR:VOLT:LEV 3V') # ‘ Source level –1.5 VOLT
	# 	self.yoko.write(':SENS:STAT ON') #‘ Measurement ON
	# 	self.yoko.write(':SENS:FUNC CURR') #‘ Measurement function Current
	# 	self.yoko.write(':SENS:ITIM MIN') #‘ Integration time Minimum
	# 	self.yoko.write(':SENS:AZER:STAT OFF') # ‘ Auto zero OFF
	# 	self.yoko.write(':TRIG:SOUR EXT') #‘ Trigger source External trigger
	# 	self.yoko.write(':SOUR:DEL MIN') #‘ Source delay Minimum
	# 	self.yoko.write(':SENS:DEL 1 PLC') #‘ Measure delay 3s
	# 	self.yoko.write(':OUTP:STAT ON') #‘ Output ON

	# # Hardcode sweep
	# def Do_Slow_Sweep():
	# 	volt_reading = []
	# 	current_reading = []
	# 	setup_slow_points(inst=inst) # Set to Setup 2
	# 	self.yoko.write(':SOUR:VOLT:LEV 0.1V') # Set the level to 0.1 V
	# 	volt_reading.append(0.1)
	# 	TrigRead()
	# 	current_reading.append(self.TrigReadAsFloat2) # Generate a trigger and read the result
	# 	self.yoko.write(':SOUR:VOLT:LEV 0.2V') # Set the level to 0.2 V
	# 	volt_reading.append(0.2)
	# 	TrigRead()
	# 	current_reading.append(TrigReadAsDouble(inst))
	# 	self.yoko.write(':OUTP:STAT OFF') # Turn the output OFF
	# 	data = pd.DataFrame({
	# 			    'voltage': volt_reading,
	# 			    'current': current_reading
	# 			})

	# 	return data