import sys
import os
sys.path.append(os.path.dirname(__file__))

import time
import numpy as np
import stellarnet_driver3 as sn  # usb driver
from scipy.optimize import minimize

class Spectrometer:
    def __init__(self, address=0):
        self.id, self.__wl = sn.array_get_spec(address)
        self.integrationtime = 100  # ms
        self.numscans = 1  # one scan per spectrum
        self.smooth = 0  # smoothing factor, units unclear

    @property
    def integrationtime(self):
        return self.__integrationtime

    @integrationtime.setter
    def integrationtime(self, t):
        self.id["device"].set_config(int_time=t)
        self.__integrationtime = t

    @property
    def numscans(self):
        return self.__numscans

    @numscans.setter
    def numscans(self, n):
        self.id["device"].set_config(scans_to_avg=n)
        self.__numscans = n

    @property
    def smooth(self):
        return self.__smooth

    @smooth.setter
    def smooth(self, n):
        self.id["device"].set_config(x_smooth=n)
        self.__smooth = n

    def capture(self):
        """
        captures a spectrum from the usb spectrometer
        """
        spectrum = sn.array_spectrum(self.id, self.__wl)
        return spectrum

    def autogain(
        self, wlmin=-np.inf, wlmax=np.inf, target: float = 0.8
    ):
        """
        finds dwell time to hit desired fraction of detector max signal in a given wavelength range
        """
        if target > 1 or target < 0:
            raise ValueError(
                "Target counts must be between 0-1 (fraction of saturated counts)"
            )
        target *= 2 ** 16  # aim for some fraction of max counts (of 16 bit depth)
        mask = np.logical_and(self.__wl >= wlmin, self.__wl <= wlmax)

        def objective(integrationtime):
            self.integrationtime = integrationtime
            spectrum = self.capture()
            return spectrum[mask, 1].max()

        integrationtime_guesses = np.array([100,200,400,800])
        counts = np.array([objective(it) for it in integrationtime_guesses])
        peakedmask = counts >= (2**16) * 0.95
        p = np.polyfit(integrationtime_guesses[~peakedmask], counts[~peakedmask])

        return np.polyval(p, target).astype(int)
