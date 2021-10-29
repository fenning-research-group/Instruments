# to run in terminal:
# 2. from yokogawa_SMU import yokocontrol_0
# 3. c = yokocontrol_0.Control()

# for fast iteration on the code you can load:
# 1. import importlib
# 2. importlib.reload(yokocontrol_0)


import pyvisa
import pandas as pd
import serial
import time
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import style
mpl.rcParams.update(mpl.rcParamsDefault)

import math
import csv


# General Control Class for Yokogawa JV
class Control:
	def __init__(self):
		self.delay = 0.05
		self.__previewFigure = None
		self.__previewAxes = None
		self.connect()


	# Connect to yoko
	def connect(self, yoko_address = 'GPIB1::1::INSTR'):
		rm = pyvisa.ResourceManager()
		self.yoko = rm.open_resource(yoko_address)
		self.yoko.timeout = 1000000 


	# Turn measurment on: Init settings for source V, measure I
	def srcV_measI(self):
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
	def srcI_measV(self):
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


	# Calculate Voc
	def voc(self):
		self.srcI_measV()
		self.a_point = 0
		self.current_command()
		self.TrigRead()
		voc = self.TrigReadAsFloat
		return voc


	# Calculate Jsc 
	def isc(self):
		self.srcV_measI()
		self.v_point = 0
		self.volt_command()
		self.TrigRead()
		isc = self.TrigReadAsFloat
		return isc


	# Sweep from vmin to vmax with steps #steps using device area 3 cm^2
	def jv(self, name, vmin=-0.1, vmax=1, steps=500, area = 3, reverse = True, forward = True, preview=True, singletime=True):
		self.steps = steps
		self.area = area
		self.reverse = reverse
		self.forward = forward
		self.preview = preview

		# create voltage
		self.fwd_v = np.linspace(vmin,vmax,steps)

		# load JV settings
		if reverse:
			self.srcV_measI()
			self.do_jv_sweep(name,vstart=vmax,vend=vmin,steps=steps,area = area, direction='rev', preview=preview)
			self.rev_i = self.i[::-1]
			self.rev_j = self.j[::-1]
			time.sleep(1e-3)
		if forward:
			self.srcV_measI()
			self.do_jv_sweep(name,vstart=vmin,vend=vmax,steps=steps,area = area, direction='fwd', preview=preview)
			self.fwd_i = self.i
			self.fwd_j = self.j
			time.sleep(1e-3)

		#Option: here we caluclate MPP & set voltage to MPP for aging.
		"""
		p_fwd = self.fwd_j*self.fwd_v
		vmpp_fwd = self.v[np.argmax(p_fwd)]
		p_rev = self.rev_j*self.fwd_v[::-1]
		vmp_rev = self.v[np.argmax(p_rev)]
		vmp = (vmp_fwd+vmp_rev)/2
		self.yoko.write(':SOUR:VOLT:LEV '+str(vmpp)+'V') # Source level MPP
		"""

		# have options to save data if its just a single time
		if singletime:
			data_IV = pd.DataFrame({
					'voltage': self.fwd_v,
				    'current_rev': self.rev_i,
				    'current_fwd' : self.fwd_i
				})

			data_JV = pd.DataFrame({
					'voltage': self.fwd_v,
				    'current_rev': self.rev_j,
				    'current_fwd' : self.fwd_j
				})
		
			data_JV.to_csv(f'{name}_JV.csv') 


	def do_jv_sweep(self,name,vstart,vend,steps,area, direction, preview):
		
		# create voltage and current arrays
		self.i = np.zeros(steps)
		self.v = np.linspace(vstart, vend, steps) 

		# set voltage, measure current
		for idx, v_point in enumerate(self.v): 
			self.v_point = v_point 
			self.volt_command()
			self.TrigRead()  
			self.i[idx] = self.TrigReadAsFloat

		# turn off output/measurement
		self.output_off() 

		# calc j, if isc < 0, mult jsc by -1 so j values are positive, keep i as raw data
		isc_mult = 1
		if self.i[np.where(np.diff(np.signbit(self.v)))[0]] < 0:
			isc_mult = -1
		self.j = isc_mult*self.i/(area*0.001)

		# preview sweeped data
		if preview:
			self._preview(self.v, self.j, f'{name}_{direction}')



	# Code for time series with total time and breaktime defined
	def tseries_jv(self, name, vmin=-0.1, vmax=1, steps=500, area = 3, reverse = True, forward = True, preview=True, totaltime=3600, breaktime=60):
		self.filename = f'{name}_IV_Timeseries.csv'
		self.name = name
		self.vmin = vmin
		self.vmax = vmax
		self.steps = steps
		self.area = area 
		self.reverse = reverse
		self.forward = forward
		self.preview = preview
		self.totaltime = totaltime	
		self.breaktime = breaktime 

		# Create easier to understand time variables for header
		self.hours_tottime = math.floor(self.totaltime/(60*60))
		self.min_tottime = math.floor((self.totaltime-self.hours_tottime*60*60)/60)
		self.sec_tottime = math.floor((self.totaltime-self.hours_tottime*60*60-self.min_tottime*60))
		self.hours_breaktime = math.floor(self.breaktime/(60*60))
		self.min_breaktime = math.floor((self.breaktime-self.hours_breaktime*60*60)/60)
		self.sec_breaktime = math.floor((self.breaktime-self.hours_breaktime*60*60-self.min_breaktime*60))


		voltage_fwd = np.linspace(vmin, vmax, steps)


		# iterate through using machine time (sleep doesnt account for time to run)
		scanning = True
		tstart = time.time()
		tend = tstart+self.totaltime
		tnext = tstart
		first_scan = 0

		# loop to manage time steps
		while scanning:
			#deal with time and name, call jv function
			self.current_time = int(tnext-tstart)
			# the name shoould be whatever is fed into it for now
			#self.name = self.name.split('_')[0]
			namelong = (f'{self.name}_{self.current_time}')
			self.jv(namelong, vmin, vmax, steps, area, reverse, forward, preview, False)
			
			if first_scan == 0:
				#self.save_step_0()		
				#self.save_step_1()
				self.save_init()

			self.save_append()

			first_scan += 1
			tnext += breaktime
			if tnext > tend:
				scanning = False
			while time.time() < tnext:
				time.sleep(1)




	# Manages preview
	def _preview(self, v, j, label): 
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


	# intial save (just voltage)
	def save_init(self):
		with open(f'{self.name}_IV_Timeseries.csv','w',newline='') as f:
			JVFile = csv.writer(f)
			
		data_df = pd.DataFrame({
			'index': np.arange(self.steps),
			f'V__fwd': self.fwd_v}).T
		data_df.to_csv(self.filename, mode='a',header=False,sep=',')
		del data_df


	# append I_epochtime_direction
	def save_append(self):
		new_data_df = pd.DataFrame({
	    f'I_{int(time.time())}_rev': self.rev_i,
	    f'I_{int(time.time())}_fwd': self.fwd_i,
		}).T

		new_data_df.to_csv(self.filename, mode='a', header=False, sep=',')
		del new_data_df



# for reading the saved csv back into pandas in post processing:
# df = pd.read_csv('filename.csv', header = 5, sep=',').T
# df.columns = df.iloc[0]
# df = df.iloc[1: , :]


## OLD CODE

# initial save (header + voltage)
	def save_init_old(self):
		with open(f'{self.name}_IV_Timeseries.csv','w',newline='') as f:
			JVFile = csv.writer(f)
			# no header for now
			JVFile.writerows([['### Header Start ###']])
			JVFile.writerows([['Name',f'{self.name}']])
			JVFile.writerows([['EPOCH Start',f'{time.time()}']])
			JVFile.writerows([['Device Area',f'{self.area}']])
			JVFile.writerows([['Min Voltage',f'{self.vmin}']])
			JVFile.writerows([['Max Voltage',f'{self.vmax}']])
			JVFile.writerows([['Voltage Steps',f'{self.steps}']])
			JVFile.writerows([['Reverse Scan',f'{self.reverse}']])
			JVFile.writerows([['Forward Scan',f'{self.forward}']])
			JVFile.writerows([['Total Time',f'{self.totaltime} sec ({self.hours_tottime} h {self.min_tottime} m {self.sec_tottime} s)']])
			JVFile.writerows([['Time Between Scan',f'{self.breaktime} sec ({self.hours_breaktime} h {self.min_breaktime} m {self.sec_breaktime} s)']])
			JVFile.writerows([['### Header End ###']])

		data_df = pd.DataFrame({
			'index': np.arange(self.steps),
			f'V_{self.current_time}_fwd': self.fwd_v}).T
		data_df.to_csv(self.filename, mode='a',header=False,sep=',')
		del data_df


	# append current data
	def save_append_old(self):
		new_data_df = pd.DataFrame({
	    f'I_{self.current_time}_fwd': self.fwd_i,
	    f'I_{self.current_time}_rev': self.rev_i,
		}).T

		new_data_df.to_csv(self.filename, mode='a', header=False, sep=',')
		del new_data_df

