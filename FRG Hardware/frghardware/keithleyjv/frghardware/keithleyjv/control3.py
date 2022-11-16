from pymeasure.instruments.keithley import Keithley2400
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time
import csv
# import serial
# from frghardware.keithleyjv import Keithley2400_dev


class Control:


	def __init__(self, area = 3, address='GPIB0::22::INSTR'):
		"""
			Initializes Keithley 2400 class SMUs
		"""
		self.area = area
		self.pause = 0.05
		self.wires = 4
		self.compliance_current = 1.05 # A
		self.compliance_voltage = 2 # V
		self.buffer_points = 2
		self.counts = 2
		self.__previewFigure = None
		self.__previewAxes = None
		self.connect(keithley_address=address)


	def help(self):
		"""
			Prints useful information to terminal
		"""
		output = "Variables\n"
		output += f'self.area = {self.area}\n'
		output += f'self.wires = {self.wires}\n'
		output += f'self.compliance_current = {self.compliance_current}\n'
		output += f'self.compliance_voltage = {self.compliance_voltage}\n'
		print(output)


	def connect(self, keithley_address):
		"""
			Connects to the GPIB interface
		"""
		self.keithley = Keithley2400(keithley_address)
		self.keithley.reset()
		self.keithley.use_front_terminals()
		self.keithley.apply_voltage()
		self.keithley.wires = self.wires
		self.keithley.compliance_current = self.compliance_current
		self.keithley.buffer_points = self.buffer_points
		self.keithley.source_voltage = 0
		# self.shutter = serial.Serial(shutter_port)
		# self.close_shutter()


	def disconnect(self):
		"""
			Disconnects from the GPIB interface
		"""
		self.keithley.shutdown()


	def open_shutter(self):
		"""
			Opens homebuilt shutter
		"""
		# self.shutter.write(b'1')
		# self._shutteropen = True
		return


	def close_shutter(self):
		"""
			Closes homebuilt shutter
		"""
		# self.shutter.write(b'0')
		# self._shutteropen = False
		return


	def _source_voltage_measure_current(self):
		"""
			Sets up sourcing voltage and measuring current
		"""
		self.keithley.apply_voltage()
		self.keithley.measure_current()
		self.keithley.compliance_current = self.compliance_current
		self.keithley.souce_voltage = 0


	def _source_current_measure_voltage(self):
		"""
			Sets up sourcing current and measuring voltage
		"""
		self.keithley.apply_current()
		self.keithley.measure_voltage()
		self.keithley.compliance_voltage = self.compliance_voltage
		self.keithley.source_current = 0


	def _measure(self):
		"""
			Measures voltage, current, and resistance
			
			Returns:
				list(np.ndarray): voltage (V), current (A), resistance (Ohms)
		"""
		self.keithley.config_buffer(self.counts)
		self.keithley.start_buffer()
		self.keithley.wait_for_buffer()
		return self.keithley.means


	def _preview_jv(self, v, j, label):
		"""
			Appends the [voltage,current denisty] arrays to preview window.
			
			Args:
				v (np.ndarray()): voltage array
				j (np.ndarray()): current array
				label (string): label for graph
		"""
		def handle_close(evt, self):
			self.__previewFigure = None
			self.__previewAxes = None
		if self.__previewFigure is None:	#preview window is not created yet, lets make it
			plt.ioff()
			self.__previewFigure, self.__previewAxes = plt.subplots()
			self.__previewFigure.canvas.mpl_connect('close_event', lambda x: handle_close(x, self))	# if preview figure is closed, lets clear the figure/axes handles so the next preview properly recreates the handles
			plt.ion()
			plt.show()
		# for ax in self.__previewAxes:	#clear the axes
		# 	ax.clear()
		self.__previewAxes.plot(v,j, label = label)
		self.__previewAxes.legend()
		self.__previewFigure.canvas.draw()
		self.__previewFigure.canvas.flush_events()
		time.sleep(1e-4)		#pause allows plot to update during series of measurements 

# preview SPO

	def _jv_sweep(self, vstart, vend, vsteps, light = True):
		""" 
			Workhorse function to run a singular JV sweep.
			
			Args:
				vstart (foat): starting voltage for JV sweep (V)
				vend (float): ending voltage for JV sweep (V)
				vsteps (int): number of voltage steps
				light (boolean = True): boolean to describe light status
			
			Returns:
				list: Voltage (V), Current Density (mA/cm2), Current (A), and Measured Voltage (V) arrays and Light Boolean
		"""
		
		# setup v, vmeas, i
		v = np.linspace(vstart, vend, vsteps)
		vmeas = np.zeros((vsteps,))
		i = np.zeros((vsteps,))
		
		# set scan
		self._source_voltage_measure_current()
		self.keithley.source_voltage = vstart
		self.keithley.enable_source()
		if light:
			self.open_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v_
			vmeas[m], i[m], _ = self._measure()
		if light:
			self.close_shutter()
		self.keithley.disable_source()
		
		# build dataframe and return
		return v, i, vmeas, light


	def _format_jv(self, v, i, vmeas, light, name, dir, scan_number):
		"""
			Uses output of _jv_sweep along with crucial info to preview and save JV data
			
			Args:
				v (np.ndarray(float)): voltage array (output from _sweep_jv)
				i (np.ndarray(float)): current array (output from _sweep_jv)
				j (np.ndarray(float)): current density array (output from _sweep_jv)
				vmeas (np.ndarray(float)): measured voltage array (output from _sweep_jv)
				light (boolean = True): boolean to describe status of light
				name (string): name of device
				dir (string): direction -- fwd or rev
				scan_number (int): suffix for multiple scans in a row
		"""
		# calc param
		j = []
		for value in i:
			j.append(-value*1000/self.area) #amps to mA/cm2. sign flip for solar cell current convention)	
		p = [num1*num2 for num1, num2 in zip(j,vmeas)]

		# build dataframe
		data = pd.DataFrame({
			'Voltage (V)': v,
			'Current Density (mA/cm2)': j,
			'Current (A)': i,
			'Measured Voltage (V)': vmeas,
			'Power Density (mW/cm2)': p,
		})
		
		# save csv
		if light:
			light_on_off = "light"
		else:
			light_on_off = "dark"
		if scan_number is None:
			scan_n = ""
		else:
			scan_n = f'_{scan_number}'
		data.to_csv(f'{name}{scan_n}_{dir}_{light_on_off}.csv')

		# preview
		self._preview_jv(v, j, f'{name}{scan_n}_{dir}_{light_on_off}')
		
		return data


	def _format_spo(self, v, i, vmeas, name):

		# calc params
		j = []
		for value in i:
			j.append(-value*1000/self.area) #amps to mA/cm2. sign flip for solar cell current convention)	
		p = [num1*num2 for num1, num2 in zip(j,vmeas)]

		# build dataframe
		data = pd.DataFrame({
			'Voltage (V)': v,
			'Current Density (mA/cm2)': j,
			'Current (A)': i,
			'Measured Voltage (V)': vmeas,
			'Power Density (mW/cm2)': p,
		})

		# save csv
		data.to_csv(f'{name}_SPO.csv', sep=',')

		# preview

		return data


	def jsc(self, printed = True) -> float:
		"""
			Conducts a short circut current density measurement
			
			Args:
				printed (boolean = True): boolean to determine if jsc is printed
			
			Returns:
				float: Short Circut Current Density (mA/cm2)
		"""
		self._source_voltage_measure_current()
		self.keithley.source_voltage = 0
		self.keithley.enable_source()
		self.open_shutter()
		isc = -self._measure()[1]
		jsc_val = isc*1000/self.area
		self.close_shutter()
		self.keithley.disable_source()
		if printed:
			print(f'Isc: {isc:.3f} A, Jsc: {jsc_val:.2f} mA/cm2')
		return jsc_val


	def voc(self, printed = False) -> float:
		"""
			Conduct a Voc measurement
			
			Args:
				printed (boolean = True): boolean to determine if voc is printed 
			
			Returns:
				float: Open circut voltage (V)
		"""
		self._source_current_measure_voltage()
		self.souce_current = 0
		self.keithley.enable_source()
		self.open_shutter()
		voc_val = self._measure()[0]
		self.close_shutter()
		self.keithley.disable_source()
		if printed:
			print(f'Voc: {voc_val*1000:.2f} mV')
		return voc_val


	def jv(self, name, direction, vmin, vmax, vsteps = 50, light = True, preview = True):
		"""
			Conducts a JV scan, previews data, saves file
			
			Args:
				name (string): name of device
				direction (string): direction -- fwd, rev, fwdrev, or revfwd
				vmin (float): start voltage for JV sweep (V)
				xmax (float): end voltage for JV sweep (V)
				vsteps (int): number of voltage steps between max and min
				light (boolean = True): boolean to describe status of light
				preview (boolean = True): boolean to determine if data is plotted
		"""

		# fwd is going to be from the lower abs v to higher abs v, reverse will be opposite
		if abs(vmin) < abs(vmax):
			v0 = vmin
			v1 = vmax
		elif abs(vmin) > abs(vmax):
			v0 = vmax
			v1 = vmin

		# seperate on call using _jv_sweep and _format_jv functions for light and dark
		if light:
			if (direction == 'fwd'):
				v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = True)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=None)
			elif (direction == 'rev'):
				v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = True)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=None)
			elif (direction == 'fwdrev'):
				v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = True)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=None)
				v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = True)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=None)
			elif (direction == 'revfwd'):
				v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = True)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=None)
				v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = True)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=None)
		if not light:
			if (direction == 'fwd'):
				v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = False)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=None)
			elif (direction == 'rev'):
				v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = False)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=None)
			elif (direction == 'fwdrev'):
				v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = False)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=None)
				v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = False)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=None)
			elif (direction == 'revfwd'):
				v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = False)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=None)
				v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = False)
				data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=None)


	def spo(self, name, vstart, viter, vstep, delay):
		""" 
			Function to run a SPO test.
			
			Args:
				name (string): name of device/file
				vstart (foat): starting voltage SPO (V)
				viter (int): number of iterations in tracking
				vstep (int): voltage to iterate SPO by (V)
			
			Returns:
				list(np.array): Voltage (V), Current density (mA/cm2), Current (A), and Measure Voltage (V)
		"""
		
		# setup v, vmeas, i arrays for MPP tracking
		v = [] # positive
		vmeas = [] # positive
		i = [] # negative
		
		# setup keithly config
		self._source_voltage_measure_current()
		self.open_shutter()
		self.keithley.source_voltage = 0
		self.keithley.enable_source()
		
		# do first two measurement (just store in correct spot)
		vapplied = vstart
		self.keithley.source_voltage = vapplied
		time.sleep(delay)
		tempv, tempi, _ = self._measure()
		vmeas.append(tempv)
		v.append(vapplied)
		i.append(tempi)
		
		# do 2nd measurement (just store in correct spot)
		vapplied += vstep
		self.keithley.source_voltage = vapplied
		time.sleep(delay)
		tempv, tempi, _ = self._measure()
		vmeas.append(tempv)
		v.append(vapplied)
		i.append(tempi)
		
		# iterate
		for n in range(0,viter):

			p0 = vmeas[-2]*i[-2]
			p1 = vmeas[-1]*i[-1]

			# print('-1',vmeas[-1],i[-1],p1)
			# print('-2',vmeas[-2],i[-2],p0)

			if p1 <= p0: 
				vapplied += v[-1]-v[-2] # power increased -> same direction
			else:
				vapplied -= v[-1]-v[-2] # power decreased -> other direction

			
			# apply voltage, measure current and voltage
			self.keithley.source_voltage = vapplied
			time.sleep(delay)
			tempv, tempi, _ = self._measure()
			
			# update dictionary & arrays
			vmeas.append(tempv)
			v.append(vapplied)
			i.append(tempi)
		
		# shutoff keithley
		self.keithley.disable_source()
		self.close_shutter()
		
		# save data
		data = self._format_spo(v=v,i=i,vmeas=vmeas,name=name)


	def jv_time(self, name, direction, vmin, vmax, vsteps = 50, light = True, preview = False, interval = 3600, interval_count = 24*7):
		"""
			Conducts multiple JV scans over a period of time, previews data, saves file
			
			Args:
				name (string): name of device
				direction (string): direction -- fwd, rev, fwdrev, or revfwd
				vmin (float): minimum voltage for JV sweep (V)
				xmax (float): maximum voltage for JV sweep (V)
				vsteps (int): number of voltage steps between max and min
				light (boolean = True): boolean to describe status of light
				preview (boolean = True): boolean to determine if data is plotted
				interval (float): time between JV scans (s)
				interval_count (int): number of times to repeat interval
		"""
		
		# Cycle through # of times selected by user
		for n in range(0, interval_count):
			
			# handle appending nunber if neccisary
			if interval_count == 0:
				suffix = None
			else:
				suffix = n
					
			# fwd is going to be from the lower abs v to higher abs v, reverse will be opposite
			if abs(vmin) < abs(vmax):
				v0 = vmin
				v1 = vmax
			elif abs(vmin) > abs(vmax):
				v0 = vmax
				v1 = vmin

			# seperate on call using _jv_sweep and _format_jv functions for light and dark
			if light:
				if (direction == 'fwd'):
					v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = True)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=n)
				elif (direction == 'rev'):
					v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = True)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=n)
				elif (direction == 'fwdrev'):
					v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = True)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=n)
					v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = True)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=n)
				elif (direction == 'revfwd'):
					v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = True)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=n)
					v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = True)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=n)
			if not light:
				if (direction == 'fwd'):
					v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = False)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=n)
				elif (direction == 'rev'):
					v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = False)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=n)
				elif (direction == 'fwdrev'):
					v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = False)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=n)
					v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = False)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=n)
				elif (direction == 'revfwd'):
					v, i, vmeas, light = self._jv_sweep(vstart = v1, vend = v0, vsteps = vsteps, light = False)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='rev', scan_number=n)
					v, i, vmeas, light = self._jv_sweep(vstart = v0, vend = v1, vsteps = vsteps, light = False)
					data = self._format_jv(v=v, i=i, vmeas=vmeas, light=light, name=name, dir='fwd', scan_number=n)
			
			if n < interval_count-1:
				time.sleep(interval)


	def voc_time(self, name, interval = 3600, interval_count = 24*7, preview = False):
		"""
			Conducts multiple Voc scans over a period of time, preveiws data, saves file
			
			Args:
				name (string) : name of device
				interval (float) : time between JV scans (s)
				interval_count (int): number of times to repeat interval
				preview (boolean = False): boolean to determine if data is plotted
		"""
		
		# create header
		data_df = pd.DataFrame(columns = ["Time", "Voc (V)"])
		data_df.to_csv(f'{name}_voc.csv', sep = ',')
		del data_df
		t = 0
		
		for n in range(0, interval_count):
			if (interval_count is None):
				suffix = ""
			elif (interval_count == 0):
				suffix = ""
			else:
				suffix = f'{n}'
			
			voc_val = self.voc(printed = preview)
			new_data_df = pd.DataFrame(data=zip([t],[voc_val]))
			new_data_df.to_csv(f'{name}_voc.csv', mode='a', header=False, sep=',')
			del new_data_df
		
			if n < interval_count-1:
				time.sleep(interval)
				t += interval


	def jsc_time(self, name, interval = 3600, interval_count = 24*7, preview = False):
		"""
			Conducts multiple jcc scans over a period of time, preveiws data, saves file
			
			Args:
				name (string) : name of device
				interval (float) : time between JV scans (s)
				interval_count (int): number of times to repeat interval
				preview (boolean = False): boolean to determine if data is plotted
		"""
		
		# create header
		data_df = pd.DataFrame(columns = ["Time", "Jsc (mA/cm2)"])
		data_df.to_csv(f'{name}_jsc.csv', sep = ',')
		del data_df
		t = 0
		
		for n in range(0, interval_count):
			jsc_val = self.jsc(printed = preview)
			new_data_df = pd.DataFrame(data=zip([t],[jsc_val]))
			new_data_df.to_csv(f'{name}_jsc.csv', mode='a', header=False, sep=',')
			del new_data_df
			
			if n < interval_count-1:
				time.sleep(interval)
				t += interval






## OLD STUFF -- Probably Not Needed anymore

	# def _set_buffer(self, npts):
	# 	self.keithley.disable_buffer()
	# 	self.keithley.buffer_points = self.counts
	# 	self.keithley.reset_buffer()

	# def _parse_buffer(self, npts):
	# 	alldata = self.keithley.buffer_data
	# 	means = np.zeros((npts,))
	# 	stds = np.zeros((npts,))
	# 	for i in range(npts):
	# 		idx = slice(i*npts, (i+1)*npts)
	# 		means[i] = np.mean(alldata[idx])
	# 		stds[i] = np.std(alldata[idx])
	# 	return {
	# 		'mean':means,
	# 		'std':stds
	# 	}

	# def volt_sweep(self, startV=0, stopV=1.5, stepV=50, compliance=5, delay=10.0e-2):
	# 	num = int(float(stopV - startV) / float(stepV)) + 1
	# 	voltRange = 2 * max(abs(stopV), abs(startV))
	# 	# self.keithley.write(":SOUR:VOLT 0.0")
	# 	self.keithley.write(":SENS:CURR:PROT %g" % 10)
	# 	self.keithley.write(":SENS:VOLT:PROT %g" % compliance)
	# 	self.keithley.write(":SOUR:DEL %g" % delay)
	# 	self.keithley.write(":SOUR:VOLT:RANG %g" % voltRange)
	# 	self.keithley.write(":SOUR:SWE:RANG FIX")
	# 	self.keithley.write(":SOUR:VOLT:MODE SWE")
	# 	self.keithley.write(":SOUR:SWE:SPAC LIN")
	# 	self.keithley.write(":SOUR:VOLT:STAR %g" % startV)
	# 	self.keithley.write(":SOUR:VOLT:STOP %g" % stopV)
	# 	self.keithley.write(":SOUR:VOLT:STEP %g" % stepV)
	# 	self.keithley.write(":TRIG:COUN %d" % num)
	# 	# if backward:
	# 	#     voltages = np.linspace(stopV, startV, num)
	# 	#     self.write(":SOUR:SWE:DIR DOWN")
	# 	# else:
	# 	voltages = np.linspace(startV, stopV, num)
	# 	self.keithley.write(":SOUR:SWE:DIR UP")
	# 	# self.connection.timeout = 30.0
	# 	self.keithley.enable_source()
	# 	data = self.keithley.values(":READ?")

	# 	# self.keithley.check_errors()
	# 	return data
	# 	# pass


	# def isc_time(self, name, totaltime=3600, breaktime=60):

	# 	# grab variables
	# 	self.name = name
	# 	self.totaltime = totaltime
	# 	self.breaktime = breaktime
	# 	self.filename = f'{name}_Isc_Timeseries.csv'

	# 	# Create easier to understand time variables for header
	# 	self.hours_tottime = math.floor(self.totaltime/(60*60))
	# 	self.min_tottime = math.floor((self.totaltime-self.hours_tottime*60*60)/60)
	# 	self.sec_tottime = math.floor((self.totaltime-self.hours_tottime*60*60-self.min_tottime*60))
	# 	self.hours_breaktime = math.floor(self.breaktime/(60*60))
	# 	self.min_breaktime = math.floor((self.breaktime-self.hours_breaktime*60*60)/60)
	# 	self.sec_breaktime = math.floor((self.breaktime-self.hours_breaktime*60*60-self.min_breaktime*60))

	# 	# iterate through using machine time (sleep doesnt account for time to run)
	# 	scanning = True
	# 	tstart = time.time()
	# 	tend = tstart+self.totaltime
	# 	tnext = tstart
	# 	first_scan = 0

	# 	# loop to manage time steps
	# 	while scanning:
	# 		#deal with time and name, call jv function
	# 		self.current_time = int(tnext-tstart)

	# 		# measure isc
	# 		self._source_voltage_measure_current()
	# 		self.source_voltage = 0
	# 		self.keithley.enable_source()
	# 		# self.open_shutter()
	# 		self.isc = self._measure()[1] #pulls current 
	# 		# self.close_shutter()
	# 		self.keithley.disable_source()

	
	# 		if first_scan == 0:
	# 			self._save_init()

	# 		self._save_append()

	# 		first_scan += 1
	# 		tnext += breaktime
	# 		if tnext > tend:
	# 			scanning = False
	# 		while time.time() < tnext:
	# 			time.sleep(1)


	# intial save (just headers)
	# def _save_init(self):
	# 	with open(f'{self.filename}','w',newline='') as f:
	# 		JVFile = csv.writer(f)

	# 	data_df = pd.DataFrame(columns = ["Time", "Current"])
	# 	data_df.to_csv(self.filename, mode='a',header=False,sep=',')
	# 	del data_df


	# # append T, Isc
	# def _save_append(self):
	# 	new_data_df = pd.DataFrame([int(time.time()),self.isc]).T

	# 	new_data_df.to_csv(self.filename, mode='a', header=False, sep=',')
	# 	del new_data_df