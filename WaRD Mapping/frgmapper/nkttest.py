def setAOTF(self, wavelength, amplitude = None, gain = None):
	### takes input to set wavelength. 
	# takes input 0-1 to set amplitude
	# takes input 0-1 to set gain (input * 0.1 = %)
	defaultWavelengths = [1700, 1750, 1800, 1850, 1900, 1902, 1950, 2000]

	## tidy up inputs
	if type(wavelength) is not list:
		wavelength = [wavelength] 
	wavelength = [round(x * 1000) for x in wavelength] 	#when talking to select, (0.001 * input = wavelength (nm)). 
	
	if amplitude is not None:
		if type(amplitude) is not list:
			amplitude = [amplitude]
		for idx, a in enumerate(amplitude):
			if a > 1:
				amplitude[idx] = 1000
				print('Note: amplitude values should be supplied in range 0-1. Setting {0} to 1'.format(a))
			elif a < 0:
				amplitude[idx] = 0
				print('Note: amplitude values should be supplied in range 0-1. Setting {0} to 0'.format(a))
			else:
				amplitude[idx] = round(a * 1000	)
	else:
		amplitude = [1000 for x in wavelength] #when talking to select,  (input * 0.1 = %. 1000 = 100%)

	if gain is not None:
		if type(gain) is not list:
			gain = [gain]
		for idx, g in enumerate(gain):
			if g > 1:
				gain[idx] = 1000
				print('Note: gain values should be supplied in range 0-1. Setting {0} to 1'.format(g))
			elif g < 0:
				gain[idx] = 0
				print('Note: gain values should be supplied in range 0-1. Setting {0} to 0'.format(g))
			else:
				gain[idx] = round(g * 1000	)
	else:
		gain = [0 for x in wavelength] #TODO when talking to select,  (input * 0.1 = %. 1000 = 100%)

	for idx in range(len(wavelength), 8):	#pad so all 8 wavelength channels are accounted for when talking to select
		wavelength = wavelength + [defaultWavelengths[idx] * 1000]
	for idx in range(len(amplitude), 8):
		amplitude = amplitude + [0]
	for idx in range(len(gain), 8):
		gain = gain + [0]

	return wavelength,amplitude,gain