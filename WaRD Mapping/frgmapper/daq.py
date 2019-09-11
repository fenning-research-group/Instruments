import ctypes
from mcculw import ul
from mcculw.enums import ScanOptions, ChannelType, ULRange, InterfaceType
from mcculw.ul import ULError
import numpy as np

board_num = 0
channel_intSphere = 0
channel_ref = 2
ai_range = ULRange.BIP5VOLTS
max_rate = 50e3

class daq(object):

    def __init__(self, channel_intSphere = 0, channel_ref = 2, rate = 10000, dwelltime = None, counts = 500):
        self.board_num = 0
        # self.ai_range = ULRange.BIP5VOLTS
        self.__rate = rate
        self.__dwelltime = dwelltime

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
        
        scan_options = ScanOptions.FOREGROUND | ScanOptions.SCALEDATA

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

        # for ch in self.channels['Label']:
        #     tempdat = {'Raw': []}
        #     for each in range(self.__countsPerChannel):
        #         tempdat['Raw'].append(ctypesArray[dataIndex])
        #         dataIndex += 1
        #     tempdat['Mean'] = np.mean(tempdat['Raw'])
        #     tempdat['Std'] = np.std(tempdat['Raw'])
        #     data[ch] = tempdat

        ul.win_buf_free(memhandle)

        return data