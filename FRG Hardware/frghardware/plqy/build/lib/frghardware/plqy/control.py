import pandas as pd
import numpy as np
import pickle as pkl
import os
import matplotlib.pyplot as plt
from time import sleep
# from pymeasure.instruments.srs import SR830
from frgtools.sr830 import SR830
from tqdm.auto import tqdm
import requests
import io

with open("FilterSlider_v1.py") as f:
    exec(f.read())

class PLQY:

    """The control class for taking PLQY using the integrating sphere and lock-in
    amplifier in SERF156.
    """
    def __init__(self, emission_wl):
        """init for the PLQY class

        Args:
            emission_wl (float): mean emisssion wavelength of the sample
        """

        with open("FilterSlider_v1.py") as f:
            exec(f.read())

        self.filterslider = FilterSlider()    
        self.lia = SR830('GPIB0::8::INSTR') # connect to the lock-in amplifier
        self.scan_types = { # look up table for the 6 types of scans and their corresponding instructions to the user
            'in_lp' : 'Put sample in beam',
            'in_nolp' : '\nKeep sample in beam, remove longpass',
            'out_lp' : '\nPut sample out of beam',
            'out_nolp' : '\nKeep sample out of beam, remove longpass',
            'empty_lp' : '\nRemove sample from integrating sphere',
            'empty_nolp' : '\nKeep sample out of integrating sphere, remove longpass'
        }
        self.sample_wl = emission_wl
        self.sample_resp = self._get_responsivity(self.sample_wl)

        self.laser_wl = 532
        self.laser_resp = self._get_responsivity(self.laser_wl)

        self.plus_minus = u"\u00B1" # this is the plus/minus unicode symbol. Makes printing this character easier
        self.data = {}
        self.code = 'Updated March 22th, 2023'

    def _take_meas(self, sample_name, scan_type, n_avg, time_constant):
        """internal function for taking a measurement

        Args:
            sample_name (str): name of the sample defined by user
            scan_type (str): one of the six scan conditions
            n_avg (int): the number of times to query the lock-in amplifier. More is not always better, as the laser drifts over periods of minutes.
        """
        self.lia.time_constant = time_constant
        sleep(10*time_constant)

        self.lia.quick_range()
            
        sleep(15*time_constant) # let the signal settle

        if self.lia.sensitivity == 2e-9:
            print('QuickRange failed, trying again...')
            self.lia.quick_range()
            if self.lia.sensitivity != 2e-9:
                print('Sensitivity is now: ', self.lia.sensitivity)
            else:
                print('QuickRange failed a second time, setting sensitivity to 1V')
                self.lia.sensitivity = 1

        raw = []
        with tqdm(total=n_avg, position=0, leave=True) as pbar:
            for m in tqdm(range(n_avg), position = 0, leave = True):
                raw.append(self.lia.get_magnitude()) # get the reading from the lock-in
                sleep(time_constant) # wait for a time constant to avoid over sampling
                pbar.update() 

        self.data[sample_name][scan_type] = np.array(raw) # add the collected data to the rest
    
    def _get_responsivity(self, emission_wl):
        """internal function to get the respnsivity of the detector at the emission wavelength

        Args:
            emission_wl (float): the mean emission wavelength of the sample

        Returns:
            float: the responsivity, arbitrary units
        """
        try: # check to make sure the file is in the directory
            # url = "https:/raw.githubusercontent.com/fenning-research-group/Python-Utilities/master/FrgTools/frgtools/Detector_Responsivity.csv"
            # download = requests.get(url).content
            fid = 'C:\\Users\\PVGroup\\Documents\\GitHub\\Python-Utilities\\FrgTools\\frgtools\\Detector_Responsivity.csv'
            # resp = pd.read_csv(url)
            resp = pd.read_csv(fid)


            return float(resp['Responsivity'][resp['Wavelength'] == emission_wl])

        except: # if not, tell the user to do so
            print(f'Detector_Responsivity.csv not able to load...check download link in code or internet connectivity:\n{url}')


    def _calc_plqy(self, data):
        """A function to calculate the PLQY based in a publication by de Mello et al.
        The most widely used method for calculating PLQY.
        https://doi.org/10.1002/adma.19970090308

        Args:
            data (dict): a dictionary containing the data. Data will be an atttribute of self

        Returns:
            tuple: (PLQY, PLQY error), resported as fractional, not percentage
        """

        E_in = data['in_lp'].mean()
        E_in_err = data['in_lp'].std()/E_in

        E_out = data['out_lp'].mean()
        E_out_err = data['out_lp'].std()/E_out

        X_in = data['in_nolp'].mean() - E_in
        X_in_err = (data['in_nolp'].std()/X_in) + E_in_err

        X_out = data['out_nolp'].mean() - E_out
        X_out_err = (data['out_nolp'].std()/X_out) + E_out_err

        X_empty = data['empty_nolp'].mean() - data['empty_lp'].mean()
        X_empty_err = (data['empty_nolp'].std()/data['empty_nolp'].mean()) + (data['empty_lp'].std()/data['empty_lp'].mean())

        E_in = E_in*(self.sample_wl/self.sample_resp)
        E_out = E_out*(self.sample_wl/self.sample_resp)

        X_in = X_in*(self.laser_wl/self.laser_resp)
        X_out = X_out*(self.laser_wl/self.laser_resp)
        X_empty = X_empty*(self.laser_wl/self.laser_resp)

        a = (X_out-X_in)/X_out
        a_err = np.sqrt(((X_out_err + X_in_err)**2) + (X_out_err**2))

        plqy = (E_in-(1-a)*E_out)/(X_empty*a)
        plqy_err = np.sqrt((E_in_err**2) + ((E_out_err + a_err)**2) + (X_empty_err**2))

        return plqy, plqy_err*plqy

    def take_PLQY(self, sample_name, n_avg, time_constant = 0.03):
        """the user-facing function to trigger a PLQY scan sequence on a sample

        Args:
            sample_name (str): the sample name you wish to use
            n_avg (int): number of averages the user wishes to take on each of the six scans. 
                         More is not always better as the laser will drift over the course of minutes.
                         I find that 10 scans is reasonable.
            time_constant(float): the length of the lock-in time constant in seconds
        """ 
        self.data[sample_name] = {}
        for scan_type in self.scan_types.keys():
            if '_lp' in scan_type and '_nolp' not in scan_type:
                # tell the user what to do
                input(f'{self.scan_types[scan_type]}...\nPress Enter to take scan')
                self.filterslider.right()
                # once in place, take the measurement
            else:
                print(f'{self.scan_types[scan_type]}...\n')
                self.filterslider.left()


            self._take_meas(sample_name, scan_type, n_avg, time_constant)

            self.filterslider.right()

        # calculate PLQY from the data, and print for the user to see
        self.data[sample_name]['plqy'], self.data[sample_name]['plqy_error'] = self._calc_plqy(self.data[sample_name])
        print(f"PLQY = {self.data[sample_name]['plqy']}{self.plus_minus}{self.data[sample_name]['plqy_error']}")
        
        # I added this in case something goes wrong so that data can be recovered if necessary
        # I prefer to save data in '.csv' format
        with open('PLQY_Data.pkl', 'wb') as f:
            pkl.dump(self.data, f)


    def save(self):
        """Save the raw data from each sample to an individual '.csv' file for later use
        """
        for k in self.data.keys():
            temp = pd.DataFrame()
            for kk in self.data[k].keys():
                if 'plqy' not in kk:
                    temp[kk] = self.data[k][kk]
                temp.to_csv(f'{k}.csv', index = False)
