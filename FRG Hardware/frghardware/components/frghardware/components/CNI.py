import serial
# laser current values 248～255, 503～511, 758～767 DOESN'T WORK. Avoid.
# This is due to software manufacturing defect from the machine itself. 

class CNI:
    def __init__(self, port = 'COM4'):
        self.__Byte_curr = [None]*7
        self.__Byte_curr[0], self.__Byte_curr[1], self.__Byte_curr[2], self.__Byte_curr[3]= 0x55, 0xAA, 0x05, 0x03

        self.__Byte_i = [None]*5 #on off switch
        self.__Byte_i[0], self.__Byte_i[1], self.__Byte_i[2], self.__Byte_i[3], self.__Byte_i[4] = 0x55, 0xAA, 0x03, 0x01, 0x04

        self.__Byte_o = [None]*5 #on off switch
        self.__Byte_o[0], self.__Byte_o[1], self.__Byte_o[2], self.__Byte_o[3], self.__Byte_o[4] = 0x55, 0xAA, 0x03, 0x00, 0x03
        
        self.port = port
        self.connect()

    def connect(self, port = None):
        if port is None:
            port = self.port
        self._ser = serial.Serial()
        self._ser.port = port
        self._ser.baudrate = 115200
        self._ser.timeout = 1
        try:
            self._ser.open()
            print('CNI connected')
            return True
        except:
            print('CNI not connected')
            return False

    def disconnect(self):
        self._ser.close()
        return True


    def _input2list(self, laser_curr):
        padding = 6

        lcurr = int(laser_curr)#1000
        lcurr_hex = f'{lcurr:#0{padding}x}'#0x03e8
        lcurrh_list = [i for i in lcurr_hex[2:]]#['0','x',...]
        
        hi_digit_list = lcurrh_list[:2]#['0', '3']
        lo_digit_list = lcurrh_list[2:]#['e', '8']

        return hi_digit_list, lo_digit_list

    def _list2hex(self, digits_list):#add 0x to hi/lo_digit_list
        return ''.join('0x{}'.format(''.join(digits_list)))#'0x03'

    def _lcurr2hi_lo_digit(self, lcurr):
        hi_di_list, lo_di_list = self._input2list(lcurr)
        hi_di, lo_di = self._list2hex(hi_di_list), self._list2hex(lo_di_list)
        return int(hi_di,16), int(lo_di,16)#'0x03','0xe8' to 3, 232

    def _read_rx(self, rx):
        read_hex = b''.join(rx)[-3:-1]# join to prevent \x0a = \n to become a line breaker; output b'\x03\xe8'
        read_deci = int.from_bytes(read_hex, 'big')# 10
        return read_deci

    def set(self, laser_curr = None):
        self.__Byte_curr[4], self.__Byte_curr[5] = self. _lcurr2hi_lo_digit(laser_curr)
        self.__Byte_curr[6] = sum(self.__Byte_curr[2:6])#sum of Byte_curr idx 2, 3, 4, 5

        self._ser.write(serial.to_bytes(self.__Byte_curr))
        rx = self._ser.readlines()#info returned info from CNI
        lcurr = self._read_rx(rx)

        print ('laser_curr read: ', lcurr, ' per mille (max 1000)')

    def on(self):
        self._ser.write(serial.to_bytes(self.__Byte_i))
        # time.sleep(1)
        rx = self._ser.readlines()
        if b''.join(rx) == bytes(self.__Byte_i): #take out the byte code from rx
            return True
        else:
            return False

    def off(self):
        self._ser.write(serial.to_bytes(self.__Byte_o))
        rx = self._ser.readlines()
        if b''.join(rx) == bytes(self.__Byte_o): #take out the byte code from rx
            return True
        else:
            return False

