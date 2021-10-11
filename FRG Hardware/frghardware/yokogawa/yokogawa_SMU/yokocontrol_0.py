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

	def isc_settings(self):
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


	# Calculate Voc
	def voc(self):
		self.voc_settings()
		self.a_point = 0
		self.current_command()
		self.TrigRead()
		voc = self.TrigReadAsFloat
		return voc


	# Calculate Jsc 
	def isc(self):
		self.isc_settings()
		self.v_point = 0
		self.volt_command()
		self.TrigRead()
		isc = self.TrigReadAsFloat
		return isc


	# Sweep from vmin to vmax with steps #steps using device area 3 cm^2
	def jv(self, name, vmin=-0.1, vmax=1, steps=500, area = 3, reverse = True, forward = True, preview=True, singletime=True):
		
		self.area = area
		self.reverse = reverse
		self.forward = forward
		self.preview = preview

		# create voltage
		self.fwd_v = np.linspace(vmin,vmax,steps)

		# load JV settings
		if reverse:
			self.jv_settings_0()
			self.do_jv_sweep(name,vstart=vmax,vend=vmin,steps=steps,area = area, direction='rev', preview=preview)
			self.rev_i = self.i[::-1]
			self.rev_j = self.j[::-1]
			time.sleep(1e-3)
		if forward:
			self.jv_settings_0()
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


	# eventually this will get slow due to huge dataframe and constantly resaving the whole thing
	# we want to save each scan and then dump memory
	def tseries_jv(self, name, vmin=-0.1, vmax=1, steps=500, area = 3, reverse = True, forward = True, preview=True, totaltime=3600, breaktime=60):
		
		# Create easier to understand time variables & Parameter File
		# -> leaving this here instead of in new function as it would be ideal to put at top of CSV
		hours_tottime = math.floor(totaltime/(60*60))
		min_tottime = math.floor((totaltime-hours_tottime*60*60)/60)
		sec_tottime = math.floor((totaltime-hours_tottime*60*60-min_tottime*60))

		hours_breaktime = math.floor(breaktime/(60*60))
		min_breaktime = math.floor((breaktime-hours_breaktime*60*60)/60)
		sec_breaktime = math.floor((breaktime-hours_breaktime*60*60-min_breaktime*60))

		scan_info = ('########## HEADER START ##########\n'
			f'name = {name}\n'
			f'EPOCH Start = {time.time()}\n'
			f'area = {area} cm²\n'
			f'vmin = {vmin} V\n'
			f'vmax = {vmax} V\n'
			f'steps = {steps}\n'
			f'reverse scan = {reverse}\n'
			f'forward scan = {forward}\n'
			f'totaltime = {totaltime} sec ({hours_tottime} h {min_tottime} m {sec_tottime} s)\n'
			f'breaktime = {breaktime} sec ({hours_breaktime} h {min_breaktime} m {sec_breaktime} s)\n'
			'########## HEADER END ##########\n'
			)

		f = open(f'{name}_IV_Timeseries_Paramerters','w')
		f.write(scan_info)
		f.close()


		# Create file/df for data, write voltage info
		voltage_fwd = np.linspace(vmin, vmax, steps)
		output_IV = pd.DataFrame({
				'V' : voltage_fwd
			})
		output_IV.to_csv(f'{name}_IV_Timeseries.csv') 
		
		# iterate through using machine time (sleep doesnt account for time to run)
		scanning = True
		tstart = time.time()
		tend = tstart+totaltime
		tnext = tstart
		
		while scanning:
			current_time = int(tnext-tstart)
			name = name.split('_')[0]
			namelong = (f'{name}_{current_time}s')
			self.jv(namelong, vmin, vmax, steps, area, reverse, forward, preview, False)
			output_IV[f'I_rev_{current_time}'] = self.rev_i
			output_IV[f'I_fwd_{current_time}'] = self.fwd_i
			output_IV.to_csv(f'{name}_IV_Timeseries.csv')
			tnext += breaktime
			
			if tnext > tend:
				scanning = False

			while time.time() < tnext:
				time.sleep(1)


	# eventually the above program will get slow due to huge dataframe and constantly resaving the whole thing
	# this version is to open file, save info, close and repeat for larger data sets
	# due to limitations of the csv package (or my knowledge and googling skills) this requires V,I1,I2... as rows
	# i think this would eventually be faster if we moved away from np, but that requires editing other subprograms
	def tseries_jv2(self, name, vmin=-0.1, vmax=1, steps=500, area = 3, reverse = True, forward = True, preview=True, totaltime=3600, breaktime=60):
		
		# Create easier to understand time variables for header
		hours_tottime = math.floor(totaltime/(60*60))
		min_tottime = math.floor((totaltime-hours_tottime*60*60)/60)
		sec_tottime = math.floor((totaltime-hours_tottime*60*60-min_tottime*60))
		hours_breaktime = math.floor(breaktime/(60*60))
		min_breaktime = math.floor((breaktime-hours_breaktime*60*60)/60)
		sec_breaktime = math.floor((breaktime-hours_breaktime*60*60-min_breaktime*60))

		# Create file, write header/scan info and voltage info
		voltage_fwd = np.linspace(vmin, vmax, steps)
		with open(f'{name}_IV_Timeseries2.csv','w',newline='') as f:
			JVFile = csv.writer(f)
			JVFile.writerows([['### Header Start ###']])
			JVFile.writerows([['Name',f'{name}']])
			JVFile.writerows([['EPOCH Start',f'{time.time()}']])
			JVFile.writerows([['Device Area',f'{area}']])
			JVFile.writerows([['Min Voltage',f'{vmin}']])
			JVFile.writerows([['Max Voltage',f'{vmax}']])
			JVFile.writerows([['Voltasge Steps',f'{steps}']])
			JVFile.writerows([['Reverse Scan',f'{reverse}']])
			JVFile.writerows([['Forward Scan',f'{forward}']])
			JVFile.writerows([['Total Time',f'{totaltime} sec ({hours_tottime} h {min_tottime} m {sec_tottime} s)']])
			JVFile.writerows([['Time Between Scan',f'{breaktime} sec ({hours_breaktime} h {min_breaktime} m {sec_breaktime} s)']])
			JVFile.writerows([['### Header End ###']])
			JVFile.writerows([['']])

			JVFile.writerows([['V'] + voltage_fwd.tolist()])

		
		# iterate through using machine time (sleep doesnt account for time to run)
		scanning = True
		tstart = time.time()
		tend = tstart+totaltime
		tnext = tstart
		
		# loop to manage time steps
		while scanning:
			#deal with time and name, call jv function
			current_time = int(tnext-tstart)
			name = name.split('_')[0]
			namelong = (f'{name}_{current_time}s')
			self.jv(namelong, vmin, vmax, steps, area, reverse, forward, preview, False)
			
			# open file and append row for fwd and another for rev
			with open(f'{name}_IV_Timeseries2.csv','a',newline='') as f:
				JVFile = csv.writer(f)
				JVFile.writerows([[f'I_rev_{current_time}'] + self.rev_i.tolist()])
				JVFile.writerows([[f'I_fwd_{current_time}'] + self.fwd_i.tolist()])

			#iterate/wait or close
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


	# def jv(self, name, vmin=-0.1,vmax=1,steps=500, reverse = True, area = 3, preview=True):
	# 	# load JV settings
	# 	self.jv_settings_0()

	# 	# scans reverse first if scanning both rev and fwd
	# 	if reverse:
	# 		# create arrays to hold voltage and current
	# 		v = np.linspace(vmax, vmin, steps) 
	# 		i = np.zeros(steps) 

	# 		# set voltage, measure current
	# 		for idx, v_point in enumerate(v): # cycle through v array
	# 			self.v_point = v_point # load v_point
	# 			self.volt_command() # use volt_command to set voltage

	# 			self.TrigRead() # read the output of the measured parameter 

	# 			i[idx] = self.TrigReadAsFloat # set the value of current in i

	# 		self.output_off() # turn off measurment

	# 		# store data in data frame
	# 		data = pd.DataFrame({
	# 			    'voltage': v,
	# 			    'current': i
	# 			})

	# 		# print data to csv
	# 		data.to_csv(f'{name}_rev.csv')

	# 		# preview data
	# 		if preview:
	# 			j = -1*i/area/.001
	# 			self._preview(v, j, f'{name}_rev')

	# 		# return pandas dataframe
	# 		# return data_rev
	# 		time.sleep(1)


	# 	# load JV settings
	# 	self.jv_settings_0()

	# 	# create arrays to hold voltage and current
	# 	v = np.linspace(vmin, vmax, steps) 
	# 	i = np.zeros(steps) 

	# 	# set voltage, measure current
	# 	for idx, v_point in enumerate(v): # cycle through v array
	# 		self.v_point = v_point # load v_point
	# 		self.volt_command() # use volt_command to set voltage

	# 		self.TrigRead() # read the output of the measured parameter 

	# 		i[idx] = self.TrigReadAsFloat # set the value of current in i

	# 	self.output_off() # turn off measurment

	# 	# store data in dataframe
	# 	data = pd.DataFrame({
	# 		    'voltage': v,
	# 		    'current': i
	# 		})

	# 	# print data to csv
	# 	data.to_csv(f'{name}_fwd.csv') # could probably comnbine fwd and rev into 1 csv

	# 	# preview sweeped data
	# 	if preview:
	# 		j = -1*i/area/.001
	# 		self._preview(v, j, f'{name}_fwd')

	# 	# return pandas dataframe
	# 	# return data_fwd


# New code		
