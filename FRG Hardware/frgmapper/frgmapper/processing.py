import matplotlib.pyplot as plt
import h5py
import os
import numpy as np
from matplotlib_scalebar.scalebar import ScaleBar


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
