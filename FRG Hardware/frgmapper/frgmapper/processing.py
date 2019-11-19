import matplotlib.pyplot as plt
import h5py
import os
import numpy as np
from matplotlib_scalebar.scalebar import ScaleBar
from frgtools.ward import *
import cmocean
import imreg_dft as ird
from skimage.filters import gaussian
from scipy import ndimage as nd

def fitThreePointWaRD(file, celltype, plot = False):
	if str.lower(celltype) in ['albsf', 'al-bsf']:
		wl_eva = 1730
		wl_h2o = 1902
		wl_ref = 1942

		p1 = 34.53
		p2 = 1.545
		celltype = 'albsf'
	elif str.lower(celltype) in ['perc']:
		wl_eva = 1730
		wl_h2o = 1902
		wl_ref = 1942

		p1 = 29.75
		p2 = 1.367
		celltype = 'perc'
	else:
		print('Celltype Error: valid types are "albsf" or "perc"')
		return

	with h5py.File(file, 'r') as d:
	    name = d['info']['name'][()]
	    x = d['data']['relx'][()]
	    y = d['data']['rely'][()]
	    realx = d['data']['x'][()]
	    realy = d['data']['y'][()]
	    wl = d['data']['wavelengths'][()]
	    ref = d['data']['reflectance'][()]
	    time = d['data']['delay'][()]
	
	ab = -np.log(ref)	#convert reflectance values to absorbance

	allWavelengthsPresent = True
	missingWavelength = None
	for each in [wl_eva, wl_h2o, wl_ref]:
		if each not in wl:
			allWavelengthsPresent = False
			missingWavelength = each
			break

	if not allWavelengthsPresent:
		print('Wavelength Error: Necessary wavelength {0} missing from dataset - cannot fit.'.format(missingWavelength))
		return

	evaIdx = np.where(wl == wl_eva)[0]
	h2oIdx = np.where(wl == wl_h2o)[0]
	refIdx = np.where(wl == wl_ref)[0]
	
	ratio = np.divide(ab[:,:,h2oIdx]-ab[:,:,refIdx], ab[:,:,evaIdx]-ab[:,:,refIdx])[:,:,0]
	h2o = ratio*p1 + p2
	# h2o[h2o < 0] = 0	


	## Avg Reflectance Fitting
	avgRef = np.mean(ref, axis = 2)

	# h2o_reg_imputed = RegisterToDummy(
	# 		ImputeWater(h2o, avgRef > avgRef.mean()*1.2),
	# 		avgRef
	# 	)

	h2o_reg_imputed = RegisterToDummy(
			h2o,
			avgRef
		)

	## write fits to h5 file
	def fillDataset(d, name, data, description):
		if name in d.keys():
			del d[name]
		temp = d.create_dataset(name, data = data)
		temp.attrs['description'] = description

	with h5py.File(file, 'a') as d:
		if 'fits' in d.keys():
			fits = d['fits']
		else:
			fits = d.create_group('/fits')

		fillDataset(d['fits'], 'water', h2o, 'Water content (mg/cm^3) measured by WaRD.')
		fillDataset(d['fits'], 'celltype', celltype.encode('utf-8'), 'Cell architecture assumed during fitting.')
		fillDataset(d['fits'], 'wl_eva', wl_eva, 'Wavelength used as EVA absorbance point.')
		fillDataset(d['fits'], 'wl_h2o', wl_h2o, 'Wavelength used as water absorbance point.')
		fillDataset(d['fits'], 'wl_ref', wl_ref, 'Wavelength used as reference absorbance point.')
		fillDataset(d['fits'], 'poly', [p1, p2], 'Polynomial fit coefficients used to convert absorbances to water content. From highest to lowest order.')
		fillDataset(d['fits'], 'avgref', avgRef, 'Average reflectance at each point')
		fillDataset(d['fits'], 'water_reg', h2o_reg_imputed, 'Water map after registration to dummy mask + imputing to replace finger regions')
	## Plotting
	if plot:
		fig, ax = plt.subplots(1,2, figsize = (10, 8))

		im1 = ax[0].imshow(
		    h2o,
		    extent = [0, x.max(), 0, y.max()],
		    origin = 'lower',
		    vmin = 0,
		    vmax = 2
		)
		cb = fig.colorbar(im1, ax = ax[0],
		                 orientation="horizontal",fraction=0.068,anchor=(1.0,0.0), pad = 0.01)
		cb.set_label('$[H_{2}O]$  $(mg/cm^3)$')
		ax[0].set_title('Water Map')
		ax[0].axis('off')


		im2 = ax[1].imshow(
		    avgRef,
		    extent = [0, x.max(), 0, y.max()],
		    origin = 'lower',
		    vmin = 0
		)
		cb = plt.colorbar(im2, ax = ax[1],
		                 orientation="horizontal",fraction=0.068,anchor=(1.0,0.0), pad = 0.01)
		cb.set_label('Reflectance')
		ax[1].set_title('Avg Reflectance')
		plt.axis('off')
		scalebar = ScaleBar(
		    dx = 1e-3,
		    location = 'lower right',
		    color = [1, 1, 1],
		    box_alpha = 0
		)
		ax[1].add_artist(scalebar)
		plt.tight_layout()
		plt.show()

def FullSpectrumFit(wavelengths, reflectance, plot = False):
	eva_peak = 1730
	eva_tolerance = 5
	h2o_peak = 1902
	h20_tolerance = 5

	if np.mean(reflectance) > 1:
		reflectance = reflectance / 100

	absSpectrum = -np.log(reflectance)
	absPeaks, absBaseline = _RemoveBaseline(absSpectrum)

	eva_idx = np.argmin(np.abs(wavelengths - eva_peak))
	eva_abs = np.max(absPeaks[eva_idx-5 : eva_idx+5])
	eva_idx_used = np.where(absPeaks == eva_abs)[0][0]

	h2o_idx = np.argmin(np.abs(wavelengths - h2o_peak))
	h2o_abs = np.max(absPeaks[h2o_idx-5 : h2o_idx+5])
	h2o_idx_used = np.where(absPeaks == h2o_abs)[0][0]

	h2o_ratio = h2o_abs/eva_abs
	h2o_meas = (h2o_ratio - 0.002153)/.03491 #from mini module calibration curve 2019-04-09, no data with condensation risk

	if plot:
		fig, ax = plt.subplots(1,2, figsize = (8,3))

		ax[0].plot(wavelengths, absSpectrum, label = 'Raw')
		ax[0].plot(wavelengths, absBaseline, label = 'Baseline')
		ax[0].legend()
		ax[0].set_xlabel('Wavelengths (nm)')
		ax[0].set_ylabel('Absorbance (AU)')

		ax[1].plot(wavelengths, absPeaks, label = 'Corrected')
		ax[1].plot(np.ones((2,)) * wavelengths[eva_idx_used], [0, eva_abs], label = 'EVA Peak', linestyle = '--')
		ax[1].plot(np.ones((2,)) * wavelengths[h2o_idx_used], [0, h2o_abs], label = 'Water Peak', linestyle = '--')
		ax[1].legend()
		ax[1].set_xlabel('Wavelengths (nm)')
		ax[1].set_ylabel('Baseline-Removed Absorbance (AU)')

		plt.tight_layout()
		plt.show()

	return h2o_meas

def ImputeWater(data, invalid = None):
	"""
	Replace the value of invalid 'data' cells (indicated by 'invalid') 
	by the value of the nearest valid data cell

	Input:
		data:    numpy array of any dimension
		invalid: a binary array of same shape as 'data'. True cells set where data
				 value should be replaced.
				 If None (default), use: invalid  = np.isnan(data)

	Output: 
		Return a filled array. 
	"""
	#import numpy as np
	#import scipy.ndimage as nd

	if invalid is None: invalid = np.isnan(data)

	ind = nd.distance_transform_edt(invalid, return_distances=False, return_indices=True)
	return data[tuple(ind)]	

def RegisterToDummy(start, start_ref = None):
	#scale dummy mask with busbar oriented upper horizontal.

	dummy = np.zeros(start.shape)
	border = [int(np.round(x*2/53)) for x in start.shape]
	busbar = int(np.round(start.shape[0]*23/53))
	dummy[border[0]:-border[0], border[1]:-border[1]] = 0.05
	dummy[busbar:busbar+border[0],:] = 1

	if start_ref is None:
		start_ref = start
		
	start_gauss = gaussian(start_ref, sigma = 0.5)
	result = ird.similarity(
		dummy,
		start_gauss,
		numiter = 30,
		constraints = {
			'angle': [0, 360],
			'tx': [0, 2],
			'ty': [0, 2],
			'scale': [1, 0.02]
		}
	)
	
	start_reg = ird.transform_img(
		start,
		tvec = result['tvec'].round(4),
		angle = result['angle'],
		scale = result['scale']
	)
	
	return start_reg