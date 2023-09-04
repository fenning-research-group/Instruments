import serial
import time
import re
from tqdm import tqdm

class opfo: #Optics Focus, Inc.
    def __init__(self, port = 'COM3'):
        # Set stage hardware parameters
        self._screw_pitch = 5 # mm
        self._stepper_angle = 1.8 # degree
        self._subdivision = 2 # look at manual
        self._pulse_equivalent = self._screw_pitch * self._stepper_angle / (360 * self._subdivision)
#         self._actual_displacement = 23 #mm, user input here to set movement distance
#         self._pulse_number = self._actual_displacement / self._pulse_equivalent #input this to the axis
        self._speed_value = 30 #user input here to change movement speed
        self._actual_speed = (self._speed_value + 1) * 22000 * self._pulse_equivalent / 720 # look at manual
        self._time_delay_factor = 1.05
        self._longrange_time_delay_factor = 6
        self._command_interval_t = 0.2        
        self._baudrate = 9600
        self._timeout = 1
        self.port = port
        
        self.connect()
        self.check_connection()

    def connect(self, port = None):
        if port is None:
            port = self.port
        self._ser = serial.Serial()
        self._ser.port = self.port
        self._ser.baudrate = self._baudrate
        self._ser.timeout = self._timeout
        self._ser.open()
        
    def disconnect(self, port = None):
        if port is None:
            port = self.port
        self._ser.close()
        # &CHR$(13) is \r, &CHR$(10) is \n

    def check_connection(self):
        self._ser.write(bytes('?R' + '\r', 'utf-8'))
        feedback = self._ser.readline()
        if feedback == bytes('?R\rOK\n', 'utf-8'):
            print('Yes, OpFo connected')
        else:
            print('No, OpFo not connected')
        self._ser.reset_input_buffer()

    def xmove(self, actual_displacement):
        if actual_displacement is None:
            print('input your x movement value')
            return False 
        self._pulse_number = actual_displacement / self._pulse_equivalent #input this to the axis
        if actual_displacement >= 0:
            direction = 'X+'
        else:
            direction = 'X' #negative is automatically contained in pulse_number

        self._ser.write(bytes(direction +str(int(self._pulse_number)) + '\r', 'utf-8'))

    def ymove(self, actual_displacement):
        if actual_displacement is None:
            print('input your y movement value')
            return False 

        self._pulse_number = actual_displacement / self._pulse_equivalent #input this to the axis
        if actual_displacement >= 0:
            direction = 'Y+'
        else:
            direction = 'Y' #negative is automatically contained in pulse_number

        self._ser.write(bytes(direction +str(int(self._pulse_number)) + '\r', 'utf-8'))

    def calculate_waittime(self): 
    # only used for homing the axis, calculate the movement time is 
    # xdist = 100
    # slptime = xdist/actual_speed * 1.15
        # measure the axis distance to the origin
        time.sleep(0.1)
        feedback = self._ser.readline()
    #     print('feedback', feedback)
        numbers_list = re.findall(r'\d+', feedback.decode('utf-8'))

        # calculate the time it needs for the stage travel back to the origin at the current speed
        current_distance = self._pulse_equivalent * float(numbers_list[0])
        slptime = current_distance/self._actual_speed * self._time_delay_factor
    #     print('numbers_list ', numbers_list)
        return slptime

    def home_stage(self): #home in the original apparatus is to return to x = 0, y = 0, 
                      #home here written by ZJD is to move the stage to the x = 100 mm, y = 100 mm
                      # because I like center-aligned stage ^_^

        xdist = 100
        ydist = 100
        self._ser.reset_input_buffer()

        # calculate the axis distance to the origin
        self._ser.write(bytes('?X\r', 'utf-8'))# ask where x is located at
        slptime = self.calculate_waittime() #calculate how much time i need to move from x = x to x = 0
        time.sleep(self._command_interval_t)# need 0.2s between commands to send the next command

        self._ser.write(bytes('HX0\r', 'utf-8')) # home x axis
        if slptime == 0: 
            slptime = 1 # need 1s time to let X go to home 0 when it's already at home 0
                        # need the calculated waittime above to let the axis go home

        # time.sleep(slptime)
        for _ in tqdm(range(int(slptime * self._longrange_time_delay_factor)), desc="move to x = 0mm"):
            time.sleep(0.1)
        self._ser.reset_input_buffer() # need to clear the buffer, otherwise calculate_waittime 
                                #reads the HX0OK line and set the waittime Y to be 1s, which doesn't give the 
                                #system enough time to ran xmove and ymove

        self._ser.write(bytes('?Y\r', 'utf-8'))
        slptime = self.calculate_waittime()
        time.sleep(self._command_interval_t)

        self._ser.write(bytes('HY0\r', 'utf-8'))
        if slptime == 0:
            slptime = 1 

        for _ in tqdm(range(int(slptime * self._longrange_time_delay_factor)), desc="move to y = 0mm"):
            time.sleep(0.1)
        # time.sleep(slptime)

        slptime = xdist/self._actual_speed * self._time_delay_factor

        self.xmove(xdist)
            # ser.write(bytes('?X\r', 'utf-8')) # so i can't read the position while the machine is moving
            # fix, set the wait time directly to be the time it takes to travel this distance
            #test 1
            # print(ser.readline())
        for _ in tqdm(range(int(slptime * self._longrange_time_delay_factor)), desc="move to x = 100mm"):
            time.sleep(0.1)
        # time.sleep(slptime)

        slptime = ydist/self._actual_speed * self._time_delay_factor
        self.ymove(ydist)
        for _ in tqdm(range(int(slptime * self._longrange_time_delay_factor)), desc="move to y = 100mm"):
            time.sleep(0.1)
        self._ser.reset_input_buffer()
        print('\nHoming stage completed!')

    def xmove_to_coor(self, target_x_coor):
        self._ser.reset_input_buffer()
        self._ser.write(bytes('?X\r', 'utf-8'))
        time.sleep(self._command_interval_t)
        
        feedback = self._ser.readline()
        numbers_list = re.findall(r'\d+', feedback.decode('utf-8'))
        current_distance = self._pulse_equivalent * float(numbers_list[0])

        target_x = target_x_coor# mm
        x_difference = target_x - current_distance
        self.xmove(x_difference)
        slptime = x_difference/self._actual_speed * self._time_delay_factor
        
        for _ in tqdm(range(int(abs(slptime) * self._longrange_time_delay_factor)), desc=f"move to x = {target_x}mm"):
            time.sleep(0.1)

        if slptime == 0:# if this is 0,need some time between letting y move and 
                        # letting input_buffer flush
            time.sleep(self._command_interval_t)

    def ymove_to_coor(self, target_y_coor):
        self._ser.reset_input_buffer()

        self._ser.write(bytes('?Y\r', 'utf-8'))
        time.sleep(self._command_interval_t)
        
        feedback = self._ser.readline()
        numbers_list = re.findall(r'\d+', feedback.decode('utf-8'))
        current_distance = self._pulse_equivalent * float(numbers_list[0])
        
        target_y = target_y_coor# mm
        y_difference = target_y - current_distance
        self.ymove(y_difference)
        slptime = y_difference/self._actual_speed * self._time_delay_factor

        for _ in tqdm(range(int(abs(slptime) * self._longrange_time_delay_factor)), desc=f"move to y = {target_y}mm"):
            time.sleep(0.1)
        if slptime == 0: 
            time.sleep(self._command_interval_t)
