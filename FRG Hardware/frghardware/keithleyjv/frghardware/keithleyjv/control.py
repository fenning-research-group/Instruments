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
		self.counts = 50

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

	def _source_voltage_measure_current():
		self.keithley.apply_voltage()
		self.keithley.measure_current()
		self.keithley.compliance_current = 1.05
		self.keithley.souce_voltage = 0

	def _source_current_measure_voltage():
		self.keithley.apply_current()
		self.keithley.measure_voltage()
		self.keithley.compliance_voltage = 2
		self.keithley.souce_current = 0

	def _set_buffer(self, npts):
		self.keithley.disable_buffer()
		self.keithley.config_buffer(self.counts, 0)
		self.keithley.buffer_points = self.counts * npts
		self.keithley.reset_buffer()

	def _parse_buffer(self, npts):
		alldata = self.buffer_data
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

	def jsc(self):
		self._source_voltage_measure_current()
		self.keithley.enable_source()
		self.open_shutter()

		isc = -self.keithley.current

		self.close_shutter()
		self.keithley.disable_source()
		print(f'Isc: {isc} A, Jsc: {jsc*1000/self.area}')

		return jsc

	def voc(self):
		self._source_current_measure_voltage()
		self.keithley.enable_source()
		self.open_shutter()

		voc = self.keithley.voltage

		self.close_shutter()
		self.keithley.disable_source()
		print(f'Voc: {voc} V')

		return voc

	def jv(self, name, vmin = -0.2, vmax = 0.7, steps = 50):
		self._source_voltage_measure_current()
		self.keithley.source_voltage = vmin
		self._set_buffer(npts = steps)
		v = np.linspace(vmin, vmax, steps)

		self.keithley.enable_source()
		self.open_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v_
			time.sleep(self.pause)
			self.keithley.start_buffer()
			# self.keithley.wait_for_buffer()
		self.close_shutter()
		self.keithley.disable_source()

		i = -self._parse_buffer(npts = steps)['mean']
		j = i*1000/self.area #amps to mA/cm2

		data = pd.DataFrame({
		    'Voltage (V)': voltages,
		    'Current Density (mA/cm2)': j,
		    'Current (A)': i,
		})
		data.to_csv(f'{name}_light.csv')

	def darkjv(self, name, vmin = -0.2, vmax = 0.7, steps = 50):
		self._source_voltage_measure_current()
		self.keithley.source_voltage = vmin
		self._set_buffer(npts = steps)
		v = np.linspace(vmin, vmax, steps)

		self.keithley.enable_source()
		self.close_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v_
			time.sleep(self.pause)
			self.keithley.start_buffer()
		self.keithley.disable_source()

		i = self._parse_buffer(npts = steps)['mean']
		j = i*1000/self.area #amps to mA/cm2
		logj = np.log(np.abs(j))
		data = pd.DataFrame({
		    'Voltage (V)': voltages,
		    'Current Density (mA/cm2)': j,
		    'Current (A)': i,
		    'Log Current Density': logj
		})
		data.to_csv(f'{name}_dark.csv')

