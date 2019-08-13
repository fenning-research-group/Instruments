from mcculw import ul
from mcculw.enums import ULRange
from mcculw.enums import ScanOptions, ChannelType, ULRange, DigitalPortType
from mcculw.ul import ULError

board_num = 0
channel_intSphere = 0
channel_ref = 2
ai_range = ULRange.BIP5VOLTS


class daq():

    def __init__(channel_intSphere = 0, channel_ref = 2, rate = 200, dwelltime = 0.1):
        self.board_num = 0
        self.ai_range = ULRange.BIP5VOLTS
        self.rate = rate
        self.dwelltime = dwelltime
        self.countsPerChannel = round(self.dwelltime * self.rate)   #counts per channel = rate (Hz) * dwelltime (s)
        self.channels = {
            'Label': ['IntSphere', 'Reference'],
            'Number': [channel_intSphere, channel_ref],
            'Type': [ChannelType.ANALOG_DIFF, ChannelType.ANALOG_DIFF],
            'Gain': [ULRange.BIP5VOLTS, ULRange.BIP5VOLTS]
            }

        #connects to first MCC DAQ device detected. Assuming we only have the USB-1808
        devices = ul.get_daq_device_inventory(InterfaceType.ANY)
        ul.create_daq_device(board_num, devices[0])

    def read(self):
        totalCount = len(self.channels['Number']) * self.countsPerChannel
        memhandle = ul.scaled_win_buff_alloc(totalCount)
        ctypesArray = ctypes.cast(memhandle, ctypes.POINTER(ctypes.c_double))
        
        scan_options = ScanOptions.FOREGROUND | ScanOptions.SCALEDATA

        ul.daq_in_scan(
            board_num = self.board_num,
            chan_list = self.channels['Number'],
            chan_type_list = self.channels['Type'],
            gain_list = self.channels['Gain'],
            chan_count = len(self.channels['Number']),
            rate = self.rate,
            pretrig_count = 0,
            total_count = totalCount,
            memhandle = memhandle,
            options = scan_options
            )

        data = {}
        dataIndex = 0
        for ch in len(self.channels['Label']):
            tempdat = {'Raw': []}
            for each in range(self.countsPerChannel):
                tempdat['Raw'].append(ctypesArray[dataIndex])
                dataIndex += 1
            tempdat['Mean'] = mean(tempdat['Raw'])
            tempdat['Std'] = std(tempdat['Raw'])
            data[ch] = tempdat

        ul.win_buf_free(memhandle)

        return data