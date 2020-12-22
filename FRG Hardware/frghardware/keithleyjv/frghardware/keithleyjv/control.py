from pymeasure.instruments.keithley import Keithley2400
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import serial
import time

class Control:
	def __init__(self, area = 24.01):
		self.area = 24.01
		self.pause = 0.05
		self.counts = 2
		self.__previewFigure = None
		self.__previewAxes = None

		self.connect()


	def connect(self, keithley_address = 'GPIB0::20::INSTR', shutter_port = 'COM3'):
		self.keithley = Keithley2400(keithley_address)
		self.keithley.reset()
		# self.keithley.output_off_state = 'HIMP'
		self.keithley.use_front_terminals()
		self.keithley.wires = 4
		self.keithley.apply_voltage()
		
		self.keithley.compliance_current = 1.05
		self.souce_voltage = 0

		self.keithley.buffer_points = 2
		# self.shutter = serial.Serial(shutter_port)
		# self.close_shutter()

	def disconnect(self):
		self.keithley.shutdown()

	def open_shutter(self):
		# self.shutter.write(b'1')
		# self._shutteropen = True
		return
	
	def close_shutter(self):
		# self.shutter.write(b'0')
		# self._shutteropen = False
		return

	def _source_voltage_measure_current(self):
		self.keithley.apply_voltage()
		self.keithley.measure_current()
		self.keithley.compliance_current = 1.05
		self.keithley.souce_voltage = 0

	def _source_current_measure_voltage(self):
		self.keithley.apply_current()
		self.keithley.measure_voltage()
		self.keithley.compliance_voltage = 2
		self.keithley.souce_current = 0

	def _set_buffer(self, npts):
		self.keithley.disable_buffer()
		self.keithley.buffer_points = self.counts
		self.keithley.reset_buffer()

	def _parse_buffer(self, npts):
		alldata = self.keithley.buffer_data
		means = np.zeros((npts,))
		stds = np.zeros((npts,))
		for i in range(npts):
			idx = slice(i*npts, (i+1)*npts)
			means[i] = np.mean(alldata[idx])
			stds[i] = np.std(alldata[idx])
		return {
			'mean':means,
			'std':stds
		}
	
	def _preview(self, v, j, label):
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

	def measure(self):
		"""
		returns voltage, current, and resistance measured
		"""
		self.keithley.config_buffer(self.counts)
		self.keithley.start_buffer()
		self.keithley.wait_for_buffer()
		return self.keithley.means

	def jsc(self):
		self._source_voltage_measure_current()
		self.source_voltage = 0
		self.keithley.enable_source()
		self.open_shutter()

		isc = -self.measure()[1]
		jsc = isc*1000/self.area
		self.close_shutter()
		self.keithley.disable_source()
		print(f'Isc: {isc:.3f} A, Jsc: {jsc:.2f} mA/cm2')

		return jsc

	def voc(self):
		self._source_current_measure_voltage()
		self.souce_current = 0
		self.keithley.enable_source()
		self.open_shutter()

		voc = self.measure()[0]

		self.close_shutter()
		self.keithley.disable_source()
		print(f'Voc: {voc*1000:.2f} mV')

		return voc

	def jv(self, name, vmin = -0.2, vmax = 0.7, steps = 50, preview = True):
		self._source_voltage_measure_current()
		self.keithley.source_voltage = vmin
		# self._set_buffer(npts = steps)
		v = np.linspace(vmin, vmax, steps)
		vmeas = np.zeros((steps,))
		i = np.zeros((steps,))

		self.keithley.enable_source()
		self.open_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v_
			vmeas[m], i[m], _ = self.measure()
			i[m] *= -1 #illuminated jv current sign convention is flipped
		self.close_shutter()
		self.keithley.disable_source()
		j = i*1000/self.area #amps to mA/cm2

		data = pd.DataFrame({
		    'Voltage (V)': v,
		    'Current Density (mA/cm2)': j,
		    'Current (A)': i,
		    'Measured Voltage (V)': vmeas
		})
		data.to_csv(f'{name}_light.csv')

		if preview:
			self._preview(v, j, f'{name}_light')

	def darkjv(self, name, vmin = -0.2, vmax = 0.7, steps = 50, preview = True):
		self._source_voltage_measure_current()
		self.keithley.source_voltage = vmin
		# self._set_buffer(npts = steps)
		v = np.linspace(vmin, vmax, steps)
		vmeas = np.zeros((steps,))
		i = np.zeros((steps,))

		self.keithley.enable_source()
		self.open_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v_
			vmeas[m], i[m], _ = self.measure()
		self.close_shutter()
		self.keithley.disable_source()
		j = i*1000/self.area #amps to mA/cm2

		logj = np.log(np.abs(j))
		data = pd.DataFrame({
		    'Voltage (V)': v,
		    'Current Density (mA/cm2)': j,
		    'Current (A)': i,
		    'Log Current Density': logj
		})
		data.to_csv(f'{name}_dark.csv')

		if preview:
			self._preview(v, j, f'{name}_dark')

