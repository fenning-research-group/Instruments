from pymeasure.instruments.keithley import Keithley2400
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import serial
import time
import math
import csv

#!/usr/bin/env python3

'''
import serial
import matplotlib.pyplot as plt

script = """
# hashes make comments
# @ on a read specifies the parser for the read data

*RST
:SENS:FUNC:CONC OFF    #Turn off concurrent functions
:SOUR:FUNC VOLT        #Set supply to voltage
:SENS:FUNC 'CURR:DC'   #Set measurement to DC current
:SENS:CURR:PROT 20E-3  #Set compliance current
:SOUR:VOLT:START 0     #Set Start Voltage
:SOUR:VOLT:STOP 10     #Set Stop Voltage
:SOUR:VOLT:STEP 1      #Set Voltage Step
:SOUR:VOLT:MODE SWE    #Enable sweep mode
:SOUR:SWE:RANG AUTO    #Set range to auto
:SOUR:SWE:SPAC LIN     #Use linear sweep
:TRIG:COUN 10          #Number of measurements(should be compatable with START|STOP|STEP)
:SOUR:DEL 0.1          #Delay between Voltage set and current measure
:FORM:ELEM VOLT,CURR   #Format of output
:OUTP ON               #Enable HV
:READ? @IV             #Read back measurements
:OUTP OFF              #Turn off output
         """

def process_script():
    global script
    script = script.splitlines()
    script = [line.split('#')[0].strip() for line in script]
    script = [line for line in script if len(line) > 0]
    for i, line in enumerate(script):
        line = line.split('@')
        if len(line) == 1:
            script[i] = (line[0]+'\n',None)
        else:
            script[i] = (line[0].strip()+'\n',line[1])

def read(ser):
    data = bytes()
    endl = '\n'.encode('ascii')[0]
    while True:
        data += ser.read(1)
        if data[-1] == endl:
            break
    return data.decode('ascii')

def parse(parser, result):
    if parser == "IV":
        result = result.split(',')
        current = []
        voltage = []
        for i, item in enumerate(result):
            if not i % 2:
                voltage.append(float(item))
            else:
                current.append(float(item))
        for v, c in zip(voltage, current):
            print("{0:+10.5e}  {1:+10.5e}".format(v,c))
        plt.xlabel('Voltage(Volts)')
        plt.ylabel('Current(Amps)')
        plt.plot(voltage,current,'.')
    else:
        raise NotImplementedError("This parser is not implemented: {0}".format(parser))

def main():
    global script
    process_script()
    with serial.Serial('/dev/ttyUSB1') as ser:
        for command, parser in script:
            print('==>'+command,end='')
            ser.write(command.encode('ascii'))
            if parser != None:
                parse(parser, read(ser))
                ser.flushOutput()
    plt.show()

if __name__ == '__main__':
    main();
    
'''


class Control:
    def __init__(self, area=4):
        self.area = 4
        self.pause = 0.05
        self.counts = 2
        self.__previewFigure = None
        self.__previewAxes = None
        self.connect()

    def connect(self, keithley_address="GPIB1::22::INSTR", shutter_port="COM3"):
        self.keithley = Keithley2400(keithley_address)
        self.keithley.reset()
        # self.keithley.output_off_state = 'HIMP'
        self.keithley.use_front_terminals()
        self.keithley.wires = 4
        self.keithley.apply_voltage()
        self.keithley.compliance_current = 1.05
        self.souce_voltage = 0
        self.keithley.buffer_points = 2
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

    def _source_voltage_measure_current(self):
        self.keithley.apply_voltage()
        self.keithley.measure_current()
        self.keithley.compliance_current = 1.05
        self.keithley.souce_voltage = 0

    def _source_current_measure_voltage(self):
        self.keithley.apply_current()
        self.keithley.measure_voltage()
        self.keithley.compliance_voltage = 2
        self.keithley.souce_current = 0

    def _set_buffer(self, npts):
        self.keithley.disable_buffer()
        self.keithley.buffer_points = self.counts
        self.keithley.reset_buffer()

    def _parse_buffer(self, npts):
        alldata = self.keithley.buffer_data
        means = np.zeros((npts,))
        stds = np.zeros((npts,))
        for i in range(npts):
            idx = slice(i * npts, (i + 1) * npts)
            means[i] = np.mean(alldata[idx])
            stds[i] = np.std(alldata[idx])
        return {"mean": means, "std": stds}

    def _preview(self, v, j, label):
        def handle_close(evt, self):
            self.__previewFigure = None
            self.__previewAxes = None

        if (
            self.__previewFigure is None
        ):  # preview window is not created yet, lets make it
            plt.ioff()
            self.__previewFigure, self.__previewAxes = plt.subplots()
            self.__previewFigure.canvas.mpl_connect(
                "close_event", lambda x: handle_close(x, self)
            )  # if preview figure is closed, lets clear the figure/axes handles so the next preview properly recreates the handles
            plt.ion()
            plt.show()
        # for ax in self.__previewAxes:	#clear the axes
        # 	ax.clear()
        self.__previewAxes.plot(v, j, label=label)
        self.__previewAxes.legend()
        self.__previewFigure.canvas.draw()
        self.__previewFigure.canvas.flush_events()
        time.sleep(1e-4)  # pause allows plot to update during series of measurements

    def measure(self):
        """
        returns voltage, current, and resistance measured
        """
        self.keithley.config_buffer(self.counts)
        self.keithley.start_buffer()
        self.keithley.wait_for_buffer()
        return self.keithley.means

    def jsc(self):
        self._source_voltage_measure_current()
        self.source_voltage = 0
        self.keithley.enable_source()
        self.open_shutter()
        isc = -self.measure()[1]
        jsc = isc * 1000 / self.area
        self.close_shutter()
        self.keithley.disable_source()
        print(f"Isc: {isc:.3f} A, Jsc: {jsc:.2f} mA/cm2")
        return jsc

    def voc(self):
        self._source_current_measure_voltage()
        self.souce_current = 0
        self.keithley.enable_source()
        self.open_shutter()
        voc = self.measure()[0]
        self.close_shutter()
        self.keithley.disable_source()
        print(f"Voc: {voc*1000:.2f} mV")
        return voc

    def isc_time(self, name, totaltime=3600, breaktime=60):

        # grab variables
        self.name = name
        self.totaltime = totaltime
        self.breaktime = breaktime
        self.filename = f"{name}_Isc_Timeseries.csv"

        # Create easier to understand time variables for header
        self.hours_tottime = math.floor(self.totaltime / (60 * 60))
        self.min_tottime = math.floor(
            (self.totaltime - self.hours_tottime * 60 * 60) / 60
        )
        self.sec_tottime = math.floor(
            (self.totaltime - self.hours_tottime * 60 * 60 - self.min_tottime * 60)
        )
        self.hours_breaktime = math.floor(self.breaktime / (60 * 60))
        self.min_breaktime = math.floor(
            (self.breaktime - self.hours_breaktime * 60 * 60) / 60
        )
        self.sec_breaktime = math.floor(
            (self.breaktime - self.hours_breaktime * 60 * 60 - self.min_breaktime * 60)
        )

        # iterate through using machine time (sleep doesnt account for time to run)
        scanning = True
        tstart = time.time()
        tend = tstart + self.totaltime
        tnext = tstart
        first_scan = 0

        # loop to manage time steps
        while scanning:
            # deal with time and name, call jv function
            self.current_time = int(tnext - tstart)

            # measure isc
            self._source_voltage_measure_current()
            self.source_voltage = 0
            self.keithley.enable_source()
            # self.open_shutter()
            self.isc = self.measure()[1]  # pulls current
            # self.close_shutter()
            self.keithley.disable_source()

            if first_scan == 0:
                self.save_init()

            self.save_append()

            first_scan += 1
            tnext += breaktime
            if tnext > tend:
                scanning = False
            while time.time() < tnext:
                time.sleep(1)

    # intial save (just headers)
    def save_init(self):
        with open(f"{self.filename}", "w", newline="") as f:
            JVFile = csv.writer(f)

        data_df = pd.DataFrame(columns=["Time", "Current"])
        data_df.to_csv(self.filename, mode="a", header=False, sep=",")
        del data_df

    # append T, Isc
    def save_append(self):
        new_data_df = pd.DataFrame([int(time.time()), self.isc]).T

        new_data_df.to_csv(self.filename, mode="a", header=False, sep=",")
        del new_data_df

    def jv(self, name, vmin=-0.2, vmax=0.7, steps=50, preview=True):
        self._source_voltage_measure_current()
        self.keithley.source_voltage = vmin
        # self._set_buffer(npts = steps)
        v = np.linspace(vmin, vmax, steps)
        vmeas = np.zeros((steps,))
        i = np.zeros((steps,))

        self.keithley.enable_source()
        self.open_shutter()
        for m, v_ in enumerate(v):
            self.keithley.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        self.close_shutter()
        self.keithley.disable_source()
        # j = i*1000/self.area #amps to mA/cm2
        j = (
            -i * 1000 / self.area
        )  # amps to mA/cm2. sign flip for solar cell current convention

        data = pd.DataFrame(
            {
                "Voltage (V)": v,
                "Current Density (mA/cm2)": j,
                "Current (A)": i,
                "Measured Voltage (V)": vmeas,
            }
        )
        data.to_csv(f"{name}_light.csv")

        if preview:
            self._preview(v, j, f"{name}_light")

    def darkjv(self, name, vmin=-0.2, vmax=0.7, steps=50, preview=True):
        self._source_voltage_measure_current()
        self.keithley.source_voltage = vmin
        # self._set_buffer(npts = steps)
        v = np.linspace(vmin, vmax, steps)
        vmeas = np.zeros((steps,))
        i = np.zeros((steps,))
        self.keithley.enable_source()
        self.open_shutter()
        for m, v_ in enumerate(v):
            self.keithley.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        self.close_shutter()
        self.keithley.disable_source()
        j = i * 1000 / self.area  # amps to mA/cm2
        logj = np.log(np.abs(j))
        data = pd.DataFrame(
            {
                "Voltage (V)": v,
                "Current Density (mA/cm2)": j,
                "Current (A)": i,
                "Log Current Density": logj,
            }
        )
        data.to_csv(f"{name}_dark.csv")
        if preview:
            self._preview(v, j, f"{name}_dark")

    def longjv(
        self,
        name,
        interval_count=24,
        interval=3600,
        vmin=-0.1,
        vmax=1.2,
        steps=50,
        preview=False,
    ):
        for n in range(0, interval_count):
            # reverse
            self._source_voltage_measure_current()
            self.keithley.source_voltage = vmax
            # self._set_buffer(npts = steps)
            v = np.linspace(vmax, vmin, steps)
            vmeas = np.zeros((steps,))
            i = np.zeros((steps,))
            self.keithley.enable_source()
            self.open_shutter()
            for m, v_ in enumerate(v):
                self.keithley.source_voltage = v_
                vmeas[m], i[m], _ = self.measure()
            self.close_shutter()
            self.keithley.disable_source()
            j = -i * 1000 / self.area  # amps to mA/cm2
            data = pd.DataFrame(
                {
                    "Voltage (V)": v,
                    "Current Density (mA/cm2)": j,
                    "Current (A)": i,
                    "Measured Voltage (V)": vmeas,
                }
            )
            data.to_csv(f"{name}_rev_light{n}.csv")

            if preview:
                self._preview(v, j, f"{name}_light")
            time.sleep(5)  # Sleep for 1 hour
            self._source_voltage_measure_current()
            self.keithley.source_voltage = vmin
            # self._set_buffer(npts = steps)
            v = np.linspace(vmin, vmax, steps)
            vmeas = np.zeros((steps,))
            i = np.zeros((steps,))
            self.keithley.enable_source()
            self.open_shutter()
            for m, v_ in enumerate(v):
                self.keithley.source_voltage = v_
                vmeas[m], i[m], _ = self.measure()
            self.close_shutter()
            self.keithley.disable_source()
            j = -i * 1000 / self.area  # amps to mA/cm2
            data = pd.DataFrame(
                {
                    "Voltage (V)": v,
                    "Current Density (mA/cm2)": j,
                    "Current (A)": i,
                    "Measured Voltage (V)": vmeas,
                }
            )
            data.to_csv(f"{name}_fwd_light{n}.csv")
            if preview:
                self._preview(v, j, f"{name}_light")
            time.sleep(interval)  # Sleep for 1 hour

    def dev_jv(self, name, vmin=-0.1, vmax=1, steps=50, preview=True):
        keithley.shutdown()
        sleep(0.1)
        self._source_voltage_measure_current()
        sleep(0.1)
        self.keithley.source_voltage = vmin
        self.keithley.ramp_to_volt(vmax, steps=steps, pause=0.1)
        keithley.shutdown()
        print(keithley.voltage)

    def fwdrev_jv(self, name, vmin=-0.1, vmax=1, steps=50, preview=True):
        # reverse
        shutdown()
        sleep(0.1)

        self._source_voltage_measure_current()
        self.keithley.source_voltage = vmax

        # self._set_buffer(npts = steps)
        v = np.linspace(vmax, vmin, steps)
        vmeas = np.zeros((steps,))
        i = np.zeros((steps,))
        self.keithley.enable_source()
        self.open_shutter()
        for m, v_ in enumerate(v):
            self.keithley.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        # self.close_shutter()
        self.keithley.disable_source()
        j = -i * 1000 / self.area  # amps to mA/cm2
        data = pd.DataFrame(
            {
                "Voltage (V)": v,
                "Current Density (mA/cm2)": j,
                "Current (A)": i,
                "Measured Voltage (V)": vmeas,
            }
        )
        data.to_csv(f"{name}_rev_light.csv")

        if preview:
            self._preview(v, j, f"{name}_light")

        shutdown()
        time.sleep(5)  # Sleep in seconds

        self._source_voltage_measure_current()
        self.keithley.source_voltage = vmin
        # self._set_buffer(npts = steps)
        v = np.linspace(vmin, vmax, steps)
        vmeas = np.zeros((steps,))
        i = np.zeros((steps,))
        self.keithley.enable_source()
        self.open_shutter()
        for m, v_ in enumerate(v):
            self.keithley.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        self.close_shutter()
        self.keithley.disable_source()
        j = -i * 1000 / self.area  # amps to mA/cm2
        data = pd.DataFrame(
            {
                "Voltage (V)": v,
                "Current Density (mA/cm2)": j,
                "Current (A)": i,
                "Measured Voltage (V)": vmeas,
            }
        )
        data.to_csv(f"{name}_fwd_light.csv")
        if preview:
            self._preview(v, j, f"{name}_light")

    def fwdrev_darkjv(self, name, vmin=-0.1, vmax=1, steps=50, preview=True):
        self._source_voltage_measure_current()
        self.keithley.source_voltage = vmax
        # self._set_buffer(npts = steps)
        v = np.linspace(vmax, vmin, steps)
        vmeas = np.zeros((steps,))
        i = np.zeros((steps,))
        self.keithley.enable_source()
        self.open_shutter()
        for m, v_ in enumerate(v):
            self.keithley.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        self.close_shutter()
        self.keithley.disable_source()
        j = i * 1000 / self.area  # amps to mA/cm2
        logj = np.log(np.abs(j))
        data = pd.DataFrame(
            {
                "Voltage (V)": v,
                "Current Density (mA/cm2)": j,
                "Current (A)": i,
                "Log Current Density": logj,
            }
        )
        data.to_csv(f"{name}_rev_dark.csv")
        if preview:
            self._preview(v, j, f"{name}_dark")

        time.sleep(5)  # Sleep for 1 hour

        self._source_voltage_measure_current()
        self.keithley.source_voltage = vmin
        # self._set_buffer(npts = steps)
        v = np.linspace(vmin, vmax, steps)
        vmeas = np.zeros((steps,))
        i = np.zeros((steps,))
        self.keithley.enable_source()
        self.open_shutter()
        for m, v_ in enumerate(v):
            self.keithley.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        self.close_shutter()
        self.keithley.disable_source()
        j = i * 1000 / self.area  # amps to mA/cm2
        logj = np.log(np.abs(j))
        data = pd.DataFrame(
            {
                "Voltage (V)": v,
                "Current Density (mA/cm2)": j,
                "Current (A)": i,
                "Log Current Density": logj,
            }
        )
        data.to_csv(f"{name}_fwd_dark.csv")
        if preview:
            self._preview(v, j, f"{name}_dark")
