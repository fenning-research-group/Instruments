# FRG PL Tool

The frgpl module coordinates an 808 nm laser, a FLIR InGaAs camera, an x-y positioning stage, a Si photodetector, a Kepco power supply, and a PID controlled thermoelectrically cooled (TEC) stage to perform electroluminescence (EL) and photoluminescence (PL) measurements of solar cells. The current hardware is optimized to characterize silicon solar cells.

# Usage

## General Approach

The module uses two general methods - setMeas() and takeMeas() to queue and execute measurements. Additional methods are available to perform various calibrations, allowing for better analysis of PL images. All data is stored in memory until .save() is called, at which point all buffered measurements are written to an hdf5 file. The buffer and any sample-specific calibrations are then reset to prepare for the next sample.

## Example PL/EL/PLIV 

1. Initialize the control object
```
import frgpl
c = frgpl.control.control()
```
2. Calibrate your incident PL illumination spot
```
c.calibrateSpot()	# stage maps the laser power across the camera field of view
```
3. Load the sample onto the stage
4. Determine laser power to achieve 1-sun illumination
```
c.findOneSun(jsc = 40, area = 9)	#jsc = mA/cm2 from solar simulator JV scan, area = active cell area in cm2
```
5. Take PL image at 1 sun injection
```
c.setMeas(voltage = 0, suns = 1)
c.takeMeas(note = '1-sun PL image')	#note here is stored in hdf5 file. just for user's own purposes
```
6. Take EL image at 0.5 V bias
```
c.setMeas(voltage = 0.5, laserpower = 0)	#note - we can use laserpower (0-1 fraction of max laser power) or, if .findOneSun has been run, suns = 0-n to determine laser power. If suns is out of range, will default to laserpower = 1.
c.takeMeas(note = 'EL')
```
7. Take EL images at biases between 0.4-0.65 V for Rse fitting
```
import numpy as np
biases = np.linspace(0.4, 0.65, 26)
for b in biases:
	c.setMeas(voltage = b, laserpower = 0)
	c.takeMeas(note = 'EL for Rse fitting')
```
Alternatively, use the built in function which is essentially recreating the above lines of code:
```
c.takeRseMeas(vmpp = 0.4, voc = 0.65)	#vmpp and voc should ideally come from solar simulator JV curve. Optional third argument vstep (default value = 0.005) determines the step size used when sweeping voltage up from Vmpp to Voc.
```
8. Take biases PL images for PLIV fitting of cell parameters
```
c.takePLIVMeas(vmpp = 0.4, voc = 0.65, jsc = 40, area = 9)	#vmpp, voc, jsc should come from solar simulator. active area in cm2
```

9. Save all measurements on this sample to hdf5 file
```
c.save(samplename = 'Example Sample', note = 'Data taken on example sample')	# saves to the default directory. Sample name and note are just for users own purposes.
```

At this point, the data buffer and findOneSun calibrations (assumed to be specific to each sample) are reset. The calibrateSpot laser spot map is preserved, since that shouldn't change from sample to sample.

## PVRD2 specific example

1. Initialize the control object
```
import frgpl
c = frgpl.control.control()
```
2. Calibrate your incident PL illumination spot
```
c.calibrateSpot()	# stage maps the laser power across the camera field of view
```
3. Load the sample onto the stage, run PVRD2 measurement. Optional arguments area and vstep, but these default to the standard 2"x2" area and vstep we want for all our measurements. This command automatically does the following:
- a one sun calibration
- one sun PL image
- -12V reverse bias EL
- Vmpp-Voc EL sweep for Rse fitting
- 0.2-1 sun, Vmpp-Voc biased PL images for PLIV fitting
- saves data to default directory
```
c.takePVRD2Meas(samplename = 'GG10', note = '8585 week 2', vmpp = 0.4, voc = 0.65, jsc = 40) #vmpp, voc, jsc come from solar simulator JV measurement.
```
