import ctypes
from ctypes import c_ulonglong, cast
from _ctypes import POINTER, addressof, sizeof
from mcculw import ul
from mcculw.enums import ScanOptions, FunctionType, Status, ChannelType, ULRange, InterfaceType
from mcculw.ul import ULError
import numpy as np
import time
import os 

from _ctypes import POINTER, addressof, sizeof
from ctypes import c_double, cast
import time

from builtins import *  # @UnusedWildImport

from mcculw import ul
from mcculw.enums import ScanOptions, FunctionType, Status
# from examples.console import util
# from examples.props.ai import AnalogInputProps
from mcculw.ul import ULError
import threading

board_num = 0
channel_intSphere = 0
channel_ref = 2
ai_range = ULRange.BIP5VOLTS
max_rate = 50e3

class daq(object):

	def __init__(self, channel_intSphere = 0, channel_ref = 2, rate = 21505, dwelltime = None, counts = 500, extclock = False):
		self.board_num = 0
		# self.ai_range = ULRange.BIP5VOLTS
		self.__rate = rate
		self.__dwelltime = dwelltime
		self.acquiringBG = False
		self.useExtClock = extclock

		# prioritize dwelltime argument when setting counts/rate. if none provided, use explicitly provided counts
		if dwelltime is not None:
			self.__countsPerChannel = round(self.__dwelltime * self.__rate)   #counts per channel = rate (Hz) * dwelltime (s)
		else:
			self.__countsPerChannel = counts
			self.__dwelltime = self.__countsPerChannel / self.__rate

		self.channels = {
			'Label': ['IntSphere', 'Reference'],
			'Number': [channel_intSphere, channel_ref],
			'Type': [ChannelType.ANALOG_DIFF, ChannelType.ANALOG_DIFF],
			'Gain': [ULRange.BIP5VOLTS, ULRange.BIP5VOLTS]
			}

		# Try connecting to the DAQ
		try:
			self.connect()
		# If error "mcculw.ul.ULError: Error 1026: Board number already in use", pass 
		except:
			print("DAQ is already connected.")

	@property
	def dwelltime(self):
		return self.__dwelltime

	@dwelltime.setter
	def dwelltime(self, x):
		# sets daq counts to match desired measurement time (x, in seconds)
		self.__dwelltime = x
		self.__countsPerChannel = round(self.__dwelltime * self.__rate)
		print('Dwelltime: {0} s\nCounts: {1}\nRate: {2} Hz'.format(self.__dwelltime, self.__countsPerChannel, self.__rate))

	@property
	def rate(self):
		return self.__rate
	
	@rate.setter
	def rate(self, x):
		# sets daq counting rate, adjusts countsPerChannel to preserve dwelltime
		x = round(x)    #only integer values allowed
		if x > max_rate:
			print('Desired rate ({0} Hz) is greater than max allowed rate ({1} Hz): setting rate to {1} Hz.'.format(x, max_rate))
			x = max_rate

		self.__rate = x
		self.__countsPerChannel = round(self.__rate * self.__dwelltime)
		print('Dwelltime: {0} s\nCounts: {1}\nRate: {2} Hz'.format(self.__dwelltime, self.__countsPerChannel, self.__rate))

	@property
	def counts(self):
		return self.__countsPerChannel
	
	@rate.setter
	def counts(self, x):
		# sets daq counting rate, adjusts countsPerChannel to preserve dwelltime
		self.__countsPerChannel = round(x)  #only integer values allowed
		newrate = round(self.__countsPerChannel * self.__dwelltime)

		if newrate > max_rate:
			print('Desired rate ({0} Hz) is greater than max allowed rate ({1} Hz): setting rate to {1} Hz.'.format(x, max_rate))
			newrate = max_rate
			self.__dwelltime = self.__countsPerChannel * newrate

		self.__rate = newrate
		print('Dwelltime: {0} s\nCounts: {1}\nRate: {2} Hz'.format(self.__dwelltime, self.__countsPerChannel, self.__rate))
	
# connects the daq device
	def connect(self):
		#connects to first MCC DAQ device detected. Assuming we only have the USB-1808
		devices = ul.get_daq_device_inventory(InterfaceType.ANY)
		ul.create_daq_device(board_num, devices[0])
		return True

# disconnects the daq device
	def disconnect(self):
		ul.release_daq_device(self.board_num)
		return True

	def read(self):
		totalCount = len(self.channels['Number']) * self.__countsPerChannel
		memhandle = ul.scaled_win_buf_alloc(totalCount)
		ctypesArray = ctypes.cast(memhandle, ctypes.POINTER(ctypes.c_double))
		
		if self.useExtClock:
			# scan_options = ScanOptions.FOREGROUND | ScanOptions.SCALEDATA | ScanOptions.EXTCLOCK
			scan_options = ScanOptions.FOREGROUND | ScanOptions.SCALEDATA | ScanOptions.EXTTRIGGER
		else:
			scan_options = ScanOptions.FOREGROUND | ScanOptions.SCALEDATA
		ul.daq_set_trigger(
                board_num = self.board_num, 
                trig_source = TriggerSource.ANALOG_HW,
                trig_sense = TriggerSensitivity.RISING_EDGE,
                trig_chan = self.chan_list[0], 
                chan_type = self.chan_type_list[0],
                gain = self.gain_list[0],
                level = 2, 
                variance = 0, 
                trig_event = TriggerEvent.START)

		ul.daq_set_trigger(	
                self.board_num, 
                TriggerSource.COUNTER,
                TriggerSensitivity.ABOVE_LEVEL,
                self.chan_list[2], 
                self.chan_type_list[2],
                self.gain_list[2],
                2, 
                0, 
                TriggerEvent.START)

        # Set the stop trigger settings
        ul.daq_set_trigger(
            self.board_num, TriggerSource.COUNTER, TriggerSensitivity.ABOVE_LEVEL,
            self.chan_list[2], self.chan_type_list[2], self.gain_list[2],
            2, 0, TriggerEvent.START)

		ul.daq_in_scan(
			board_num = self.board_num,
			chan_list = self.channels['Number'],
			chan_type_list = self.channels['Type'],
			gain_list = self.channels['Gain'],
			chan_count = len(self.channels['Number']),
			rate = self.__rate,
			pretrig_count = 0,
			total_count = totalCount,
			memhandle = memhandle,
			options = scan_options
			)

		data = {}
		for ch in self.channels['Label']:
			data[ch] = {
				'Raw':[],
				'Mean': None,
				'Std': None
				}

		dataIndex = 0
		for each in range(self.__countsPerChannel):
			for ch in self.channels['Label']:
				data[ch]['Raw'].append(ctypesArray[dataIndex])
				dataIndex += 1

		for ch in self.channels['Label']:
			data[ch]['Mean'] = np.mean(data[ch]['Raw'])
			data[ch]['Std'] = np.std(data[ch]['Raw'])

		data['Reference']['Mean'] = np.ones(data['Reference']['Mean'].shape)	#set reference detector readings to 1

		ul.win_buf_free(memhandle)

		return data

	def startBG(self, filepath = "tempfile.dat"):
		#starts background DAQ acquisition. Data is written to file designated by filepath
		self.acquiringBG = True
		self.filepathBG = filepath
		self.threadBG = threading.Thread(target = self._readBG, args = (filepath,))
		self.threadBG.start()

	def stopBG(self, removefile = True):
		#stops background DAQ acquisition, returns timestamps + data stored in file
		self.acquiringBG = False
		self.threadBG.join()
		data = np.genfromtxt(self.filepathBG, delimiter = ',')
		numpts = data.shape[0]
		time = np.linspace(0,numpts,numpts+1)[1:] / self.__rate
		if removefile:
			os.remove(self.filepathBG)
		return time, data

	def _readBG(self, file_name):
		# file_name = 'C:\\Users\\PVGroup\\Desktop\\frgmapper\\Data\\20190913\\test.data'
		# totalCount = len(self.channels['Number']) * self.__countsPerChannel
		# memhandle = ul.win_buf_alloc_64(totalCount)
		# ctypesArray = ctypes.cast(memhandle, ctypes.POINTER(ctypes.c_ulonglong))

		# The size of the UL buffer to create, in seconds
		buffer_size_seconds = 2
		# The number of buffers to write. After this number of UL buffers are
		# written to file, the example will be stopped.
		num_buffers_to_write = 2


		low_chan = 0
		high_chan = 1
		num_chans = high_chan - low_chan + 1

		# Create a circular buffer that can hold buffer_size_seconds worth of
		# data, or at least 10 points (this may need to be adjusted to prevent
		# a buffer overrun)
		points_per_channel = max(self.__rate * buffer_size_seconds, 10)

		# Some hardware requires that the total_count is an integer multiple
		# of the packet size. For this case, calculate a points_per_channel
		# that is equal to or just above the points_per_channel selected
		# which matches that requirement.
		# if ai_props.continuous_requires_packet_size_multiple:
		# 	packet_size = ai_props.packet_size
		# 	remainder = points_per_channel % packet_size
		# 	if remainder != 0:
		# 		points_per_channel += packet_size - remainder

		ul_buffer_count = points_per_channel * num_chans

		# Write the UL buffer to the file num_buffers_to_write times.
		points_to_write = ul_buffer_count * num_buffers_to_write

		# When handling the buffer, we will read 1/10 of the buffer at a time
		write_chunk_size = int(ul_buffer_count / 100)

		if self.useExtClock:
			scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS | ScanOptions.SCALEDATA | ScanOptions.EXTCLOCK
		else:
			scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS | ScanOptions.SCALEDATA

		memhandle = ul.scaled_win_buf_alloc(ul_buffer_count)

		# Allocate an array of doubles temporary storage of the data
		write_chunk_array = (c_double * write_chunk_size)()

		# Check if the buffer was successfully allocated
		if not memhandle:
			print("Failed to allocate memory.")
			return

		try:
			# Start the scan
			ul.daq_in_scan(
				board_num = self.board_num,
				chan_list = self.channels['Number'],
				chan_type_list = self.channels['Type'],
				gain_list = self.channels['Gain'],
				chan_count = len(self.channels['Number']),
				rate = self.__rate,
				pretrig_count = 0,
				total_count = ul_buffer_count,
				memhandle = memhandle,
				options = scan_options
				)

			status = Status.IDLE
			# Wait for the scan to start fully
			while(status == Status.IDLE):
				status, _, _ = ul.get_status(
					board_num, FunctionType.DAQIFUNCTION)

			# Create a file for storing the data
			with open(file_name, 'w') as f:
				# print('Writing data to ' + file_name, end='')

				# Write a header to the file
				# for chan_num in range(low_chan, high_chan + 1):
				# 	f.write('Channel ' + str(chan_num) + ',')
				# f.write(u'\n')

				# Start the write loop
				prev_count = 0
				prev_index = 0
				write_ch_num = low_chan
				keepReading = True
				while status != Status.IDLE and keepReading:
					# Get the latest counts
					status, curr_count, _ = ul.get_status(
						board_num, FunctionType.DAQIFUNCTION)

					new_data_count = curr_count - prev_count

					# Check for a buffer overrun before copying the data, so
					# that no attempts are made to copy more than a full buffer
					# of data
					if new_data_count > ul_buffer_count:
						# Print an error and stop writing
						ul.stop_background(board_num, FunctionType.DAQIFUNCTION)
						print("A buffer overrun occurred")
						break

					# Check if a chunk is available
					if new_data_count > write_chunk_size:
						wrote_chunk = True
						# Copy the current data to a new array

						# Check if the data wraps around the end of the UL
						# buffer. Multiple copy operations will be required.
						if prev_index + write_chunk_size > ul_buffer_count - 1:
							first_chunk_size = ul_buffer_count - prev_index
							second_chunk_size = (
								write_chunk_size - first_chunk_size)

							# Copy the first chunk of data to the
							# write_chunk_array
							ul.scaled_win_buf_to_array(
								memhandle, write_chunk_array, prev_index,
								first_chunk_size)

							# Create a pointer to the location in
							# write_chunk_array where we want to copy the
							# remaining data
							second_chunk_pointer = cast(
								addressof(write_chunk_array) + first_chunk_size
								* sizeof(c_double), POINTER(c_double))

							# Copy the second chunk of data to the
							# write_chunk_array
							ul.scaled_win_buf_to_array(
								memhandle, second_chunk_pointer,
								0, second_chunk_size)
						else:
							# Copy the data to the write_chunk_array
							ul.scaled_win_buf_to_array(
								memhandle, write_chunk_array, prev_index,
								write_chunk_size)

						# Check for a buffer overrun just after copying the data
						# from the UL buffer. This will ensure that the data was
						# not overwritten in the UL buffer before the copy was
						# completed. This should be done before writing to the
						# file, so that corrupt data does not end up in it.
						status, curr_count, _ = ul.get_status(
							board_num, FunctionType.DAQIFUNCTION)
						if curr_count - prev_count > ul_buffer_count:
							# Print an error and stop writing
							ul.stop_background(board_num, FunctionType.DAQIFUNCTION)
							print("A buffer overrun occurred")
							break

						for i in range(write_chunk_size):
							f.write(str(write_chunk_array[i]))
							write_ch_num += 1
							if write_ch_num == high_chan + 1:
								write_ch_num = low_chan
								f.write(u'\n')
							else:
								f.write(',')
					else:
						wrote_chunk = False

					if wrote_chunk:
						# Increment prev_count by the chunk size
						prev_count += write_chunk_size
						# Increment prev_index by the chunk size
						prev_index += write_chunk_size
						# Wrap prev_index to the size of the UL buffer
						prev_index %= ul_buffer_count
						if not self.acquiringBG:	#make sure to wait until after writing to check if we should stop to avoid truncation
							keepReading = False
						# if prev_count >= points_to_write:
						# 	break
						# f.write('-----\n')
						# print('.', end='')
					else:
						# Wait a short amount of time for more data to be
						# acquired.
						time.sleep(0.01)

			ul.stop_background(board_num, FunctionType.DAQIFUNCTION)
		except ULError as e:
			pass
		finally:
			# print('Done')

			# Free the buffer in a finally block to prevent errors from causing
			# a memory leak.
			ul.win_buf_free(memhandle)