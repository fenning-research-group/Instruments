import pyvisa 
import pdb
import math
import time

# code for the Stanford Research Systems SR830 lock-in

class lockin(object):

	def __init__(self,LockinAddress='GPIB0::8::INSTR'): # Connect and send initialization commands
		rm=pyvisa.ResourceManager()
		self.handle = rm.open_resource(LockinAddress)
		# Send initialization commands
		self.handle.write('OUTX 1') # Set the communication mode to GPIB
		self.handle.write('FMOD 0') # Set to external reference mode (ref signal from the chopper wheel)
		self.handle.write('RSLP 1') # Set slope to Sine(0) for reference signal trigger
		self.handle.write('ISRC 0') # Set input signal to channel A (IMPORTANT FOR CONNECTION!)
		self.handle.write('IGND 0') # Set to floating ground
		self.handle.write('ICPL 0') # Set to AC coupling
		self.handle.write('ILIN3') 	# Use both notch filters
		self.handle.write('OFSL 3') # Set low pass filter to 24 db/octave
		self.handle.write('RMOD 2') # Set reserve mode to low noise (minimum)
		self.handle.write('DDEF 1,0') # ?? see manual p. 5-8. Display X (amplitude) on channel 1??
		self.handle.write('FAST 2') # Set data transfer ON, Windows interface
		self.SRS_TC=0 # lock in time constant
		self.SetLockinTimeConstant()
		self.SetLockinSensitivity()

	def CloseLockin(self):
		rm=pyvisa.ResourceManager()
		#self.handle.control_ren(mode) # reset to local mode
		self.handle.clear()
		rm.close()

	def LockinReadOutput(self): # read output
		self.handle.write('OUTP? 3') # Reads signal amplitude> Note: OUTP? {i} with i=1 for amplitude X, i=2 for amplitude Y of the second PSD signal, i=3 for RMS R of both PSD signals = signal amplitude Vsig, i=4 for phase theta
		Vsig=self.handle.read()
		self.handle.write('OUTP? 4') # Reads phase theta
		phase=self.handle.read()
		self.handle.write('FREQ?') # Reads the reference frequency manually set in the optical chopper
		freq=self.handle.read()
		return Vsig, phase, freq

	def SetLockinTimeConstant(self):# Method to set time constant based on chopper frequency
		[Vsig, phase, f]=self.LockinReadOutput() # Query frequency from the lockin (set on the chopper by the user)
		freq=10*math.ceil(float(f)/10) # round frequency
		tc_s = 1/(freq*10**(-3/10)) # -3 dB the freq (G=10*log(f0)?)
		
		if tc_s > 10E-6 and tc_s <= 30E-6:
			SRS_TC_N = 1
			SRS_TC = 30E-6
		elif tc_s > 30E-6 and tc_s <= 100E-6:
			SRS_TC = 100E-6
			SRS_TC_N = 2
		elif tc_s > 100E-6 and tc_s <= 300E-6:
			SRS_TC = 300E-6
			SRS_TC_N = 3
		elif tc_s > 300E-6 and tc_s <= 1E-3:
			SRS_TC = 1E-3
			SRS_TC_N = 4
		elif tc_s > 1E-3 and tc_s <= 3E-3:
			SRS_TC   = 3E-3
			SRS_TC_N = 5
		elif tc_s > 3E-3 and tc_s <= 10E-3:
			SRS_TC   = 10E-3
			SRS_TC_N = 6
		elif tc_s > 10E-3 and tc_s <= 30E-3:
			SRS_TC   = 30E-3
			SRS_TC_N = 7
		elif tc_s > 30E-3 and tc_s <= 100E-3:
			SRS_TC   = 100E-3
			SRS_TC_N = 8
		elif tc_s > 100E-3 and tc_s <= 300E-3:
			SRS_TC   = 300E-3
			SRS_TC_N = 9
		elif tc_s > 300E-3 and tc_s <= 1:
			SRS_TC   = 1
			SRS_TC_N = 10
		elif tc_s > 1 and tc_s <= 3:
			SRS_TC   = 3
			SRS_TC_N = 11
		elif tc_s > 3 and tc_s <= 10:
			SRS_TC   = 10
			SRS_TC_N = 12
		elif tc_s > 10 and tc_s <= 30:
			SRS_TC   = 30
			SRS_TC_N = 13
		elif tc_s > 30 and tc_s <= 100:
			SRS_TC   = 100
			SRS_TC_N = 14
		elif tc_s > 100 and tc_s <= 300:
			SRS_TC   = 300
			SRS_TC_N = 15
		elif tc_s > 300 and tc_s <= 1000:
			SRS_TC   = 1000
			SRS_TC_N = 16
		elif tc_s > 1E3 and tc_s <= 3E3:
			SRS_TC   = 3E3
			SRS_TC_N = 17
		elif tc_s > 3E3 and tc_s <= 10E3:
			SRS_TC   = 10E3
			SRS_TC_N = 18
		elif tc_s > 10E3 and tc_s <= 30E3:
			SRS_TC   = 30E3
			SRS_TC_N = 19

		self.SRS_TC=SRS_TC

		tc_string='OFLT '+str(SRS_TC_N)
		self.handle.write(tc_string)
		#pdb.set_trace()
	
	# set sensitivity, ie adjust amplification to avoid lockin overload (signal saturation)
	# (Do this for with the light beam on at a wavelength having the highest intensity in 1700-2000 nm range)
	def SetLockinSensitivity(self): 
		self.handle.write('SENS ?') # Query sensitivity
		sens=int(self.handle.read()) # Number corresponding to the sensitivity (manual p. 5-6)

		self.SetLockinTimeConstant() # find SRS_TC and save it as attribute
		
		time.sleep(5*self.SRS_TC)

		# Find overload status
		self.handle.write('LIAS? 2') # Query LIA status byte, bit 2 (OUTPT), corresponding to overload detection (manual p. 5-23)
		overload=int(self.handle.read())

		#pdb.set_trace()
		# if the system is overloaded
		if(overload != 0 and sens < 26): # the index corresponding to the max sensitivity is 26
			while(overload != 0 and sens < 26): # while the system is overloaded, decrease sensitivity (ie increase the index sens)
				sens=sens + 1
				sens_str='SENS '+str(sens)
				self.handle.write(sens_str)
				# Find overload status
				time.sleep(5*self.SRS_TC)
				self.handle.write('LIAS? 2') # Query LIA status byte, bit 2 (OUTPT), corresponding to overload detection (manual p. 5-23)
				overload=int(self.handle.read())
		elif(overload != 0 and sens == 26): # the index corresponding to the max sensitivity is 26
			print("System overloaded while at minimum sensitivity!")
			#break
		else:
			while(sens > 0 and overload == 0): # increase sensitivity if the system is not overloaded
				sens=sens - 1
				sens_str='SENS '+str(sens)
				self.handle.write(sens_str)
				# Find overload status
				time.sleep(5*self.SRS_TC)
				self.handle.write('LIAS? 2') # Query LIA status byte, bit 2 (OUTPT), corresponding to overload detection (manual p. 5-23)
				overload=int(self.handle.read())

			if(overload!=0): # if the system is overloaded at the end
				sens=sens+2 # decrease sensitivity
				sens_str='SENS '+str(sens)
				self.handle.write(sens_str)

				self.handle.write('LIAS? 2') # Query LIA status byte, bit 2 (OUTPT), corresponding to overload detection (manual p. 5-23)
				overload=int(self.handle.read())

		time.sleep(10*self.SRS_TC)

	# Function sweeping the wavelength over the wavelength range and measuring raw intensity to find the max

