from pymeasure.instruments.keithley import Keithley2400
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import serial

class Control:
	def __init__(self, area = 24.01):
		self.area = 24.01
		self.pause = 0.05
		self.counts = 50


	def connect(self, keithley_address = 'GPIB::1', shutter_port = 'COM3'):
		self.keithley = Keithley2400(keithley_address)
		self.keithley.reset()
		# self.keithley.output_off_state = 'HIMP'
		self.keithley.wires = 4
		self.keithley.apply_voltage()
		
		self.keithley.compliance_current = 1.05
		self.souce_voltage = 0

		self.shutter = serial.Serial(shutter_port)
		self.close_shutter()

	def disconnect(self):
		self.keithley.shutdown()


	def open_shutter(self):
		self.shutter.write(b'1')
		self._shutteropen = True

	def close_shutter(self):
		self.shutter.write(b'0')
		self._shutteropen = False

	def jsc(self):
		self.keithley.apply_voltage()
		self.keithley.compliance_current = 1.05
		self.keithley.souce_voltage = 0
		self.keithley.enable_source()
		self.open_shutter()

		isc = -self.keithley.measure_current()

		self.close_shutter()
		self.keithley.disable_source()
		print(f'Isc: {isc} A, Jsc: {jsc*1000/self.area}')

		return jsc

	def voc(self):
		self.keithley.apply_current()
		self.keithley.compliance_voltage = 2
		self.keithley.souce_current = 0
		self.keithley.enable_source()
		self.open_shutter()

		voc = self.keithley.measure_voltage()

		self.close_shutter()
		self.keithley.disable_source()
		print(f'Voc: {voc} V')

		return voc

	def jv(self, name, vmin = -0.2, vmax = 0.7, steps = 50):
		self.keithley.apply_voltage()
		self.keithley.compliance_current = 1.05
		self.keithley.source_voltage = vmin

		v = np.linspace(vmin, vmax, steps)
		i = np.zeros(v.shape)

		self.keithley.enable_source()
		self.open_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v
			self.keithley.reset_buffer()
			time.sleep(self.pause)
			self.keithley.start_buffer()
			self.keithley.wait_for_buffer()
			i[m] = self.keithley.means
			# i_std[m] = self.keithley.standard_devs
		self.close_shutter()
		self.keithley.disable_source()

		j = i*1000/self.area #amps to mA/cm2

		data = pd.DataFrame({
		    'Voltage (V)': voltages,
		    'Current Density (mA/cm2)': j
		    'Current (A)': i,
		})
		data.to_csv(f'{name}_light.csv')

	def darkjv(self, name, vmin = -0.2, vmax = 0.7, steps = 50):
		self.keithley.apply_voltage()
		self.keithley.compliance_current = 1.05
		self.keithley.source_voltage = vmin

		v = np.linspace(vmin, vmax, steps)
		i = np.zeros(v.shape)

		self.keithley.enable_source()
		self.close_shutter()
		for m, v_ in enumerate(v):
			self.keithley.source_voltage = v
			self.keithley.reset_buffer()
			time.sleep(self.pause)
			self.keithley.start_buffer()
			self.keithley.wait_for_buffer()
			i[m] = self.keithley.means
			# i_std[m] = self.keithley.standard_devs
		self.keithley.disable_source()

		j = i*1000/self.area	#amps to mA/cm2

		data = pd.DataFrame({
		    'Voltage (V)': voltages,
		    'Current Density (mA/cm2)': j
		    'Current (A)': i,
		})
		data.to_csv(f'{name}_dark.csv')

