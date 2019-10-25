import matplotlib.pyplot as plt
import h5py
import os
import numpy as np
from matplotlib_scalebar.scalebar import ScaleBar
from scipy.signal import medfilt
from matplotlib.colors import LogNorm
from matplotlib_scalebar.scalebar import ScaleBar
from skimage.filters import threshold_otsu #, threshold_adaptive
from scipy import ndimage
from tqdm import tqdm
import time

def fitRsEL(file, area = 25, plot = False):
	def cleanImage(img, bg, threshold = 3):
		mask = img > (img.mean() + threshold*img.std())	#flag values * std devs over the mean
		medvals = medfilt(img, 3) #3x3 median filter
		medvals[(0,0,-1,-1),(0,-1,0,-1)] = img[(0,0,-1,-1),(0,-1,0,-1)]# corner values become 0, not useful. Set back to original value
		img[mask] = medvals[mask]
		return img - bg

	## load data

	with h5py.File(file, 'r') as f:
		title = f['info']['name'][()].decode('utf-8')
		notes = f['settings']['notes'][()]
		idx = [b'Rse' in x for x in notes]
		fov = f['settings']['camerafov'][()]/10000	#camera FOV, converted from um to cm
		vmeas = f['data']['v'][()][idx]
		jmeas = f['data']['i'][()][idx] / area
		img = [f['data']['image'][x,:,:] for x in range(f['data']['image'].shape[0]) if idx[x]]
		img = np.array(img)
		bg = f['data']['image'][0,:,:]

	bg = cleanImage(bg, 0, 1)	#hot pixel removal on background image

	## theshold image to exclude background
	def findBoundingRectangle(mask):
		xmin = 1000
		xmax = 0
		ymin = 1000
		ymax = 0
	
		for c, v in np.ndenumerate(mask):
			if v:
				if c[0] < xmin:
					xmin = c[0]
				if c[0] > xmax:
					xmax = c[0]
				if c[1] < ymin:
					ymin = c[1]
				if c[1] > ymax:
					ymax = c[1]
			
		rectMask = np.zeros(mask.shape)
		rectMask[xmin:xmax, ymin:ymax] = 1
		return rectMask == 1


	thresholdImg = cleanImage(img[-1, :, :].copy(), bg, 1.5)
	brightimg = cleanImage(thresholdImg, bg, 1.5)
	global_thresh = threshold_otsu(brightimg)
	mask = brightimg > global_thresh
	mask = ndimage.binary_erosion(mask, iterations = 5)	#get rid of speckles
	mask = ndimage.binary_dilation(mask, iterations = 10) 
	mask = findBoundingRectangle(mask)

	## Clean up data for Rs fitting
	numpts = img.shape[0]-1
	kB = 8.617330e-5
	T = 296
	q = 1
	UT = kB*T/q  # in V

	v = np.zeros((numpts,))
	dv = np.zeros((numpts,))
	j = np.zeros((numpts,))
	phiI = np.zeros((numpts, img.shape[1], img.shape[2]))
	dphiI = np.zeros((numpts, img.shape[1], img.shape[2]))
	sumphi = np.zeros((numpts,))

	for i in range(numpts):
		v[i] = (vmeas[i] + vmeas[i+1])/2
		j[i] = (jmeas[i] + jmeas[i+1])/2
		dv[i] = vmeas[i+1] - vmeas[i]

		im1 = img[i, :, :] - bg
		im1[im1 < 0] = 0
		im2 = img[i+1, :, :] - bg
		im2[im2 < 0] = 0

		phiI[i] = (im1 + im2) / 2
		dphiI[i] = im2 - im1
		sumphi[i] = phiI[i][mask].sum()

	imeas = j*area

	## calibration constant
	areaPerPixel = area / mask.sum()
	calfit = np.polyfit(j*mask.sum(), sumphi, 1)
	CiJoi = calfit[0]

	plt.plot(j*mask.sum(), sumphi)
	plt.plot(j*mask.sum(), j*mask.sum()*calfit[0] + calfit[1], linestyle = ':')
	plt.xlabel('amps/cm2/pixel')
	plt.ylabel(u'$\Sigma\Phi$')
	plt.show()

	time.sleep(1)
	## Rs fitting
	def fitRse(phiI, dphiI):
		x = np.divide(dphiI, dv)
		y = UT * np.divide(x, phiI)
		try:
			pfit = np.polyfit(x,y,1)
			rse = -CiJoi * pfit[0] / pfit[1]
		except:
			rse = np.nan
			
		return rse

	vm = phiI.shape[1]
	vn = phiI.shape[2]

	Rse = np.zeros((vm,vn))

	with tqdm(total = vm*vn, desc = 'Fitting Rse') as pb:
		for m in range(vm):
			for n in range(vn):
		#         Rse[m,n] = pool.apply(fitRse(phiI[:,m,n], dphiI[:,m,n]))
				if mask[m,n]:
					Rse[m,n] = fitRse(phiI[:,m,n], dphiI[:,m,n])
				else:
					Rse[m,n] = np.nan                    
				pb.update(1)

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

		fillDataset(d['fits'], 'Rs_EL', Rse, 'Local series resistance (ohm*cm^2) calculated by fitting electroluminescence data.')
		# fillDataset(d['fits'], 'celltype', celltype.encode('utf-8'), 'Cell architecture assumed during fitting.')
		# fillDataset(d['fits'], 'wl_eva', wl_eva, 'Wavelength used as EVA absorbance point.')
		# fillDataset(d['fits'], 'wl_h2o', wl_h2o, 'Wavelength used as water absorbance point.')
		# fillDataset(d['fits'], 'wl_ref', wl_ref, 'Wavelength used as reference absorbance point.')
		# fillDataset(d['fits'], 'poly', [p1, p2], 'Polynomial fit coefficients used to convert absorbances to water content. From highest to lowest order.')
		# fillDataset(d['fits'], 'avgref', avgRef, 'Average reflectance at each point')

	## Plotting
	# if plot:
	# 	fig, ax = plt.subplots(1,2, figsize = (10, 8))

	# 	im1 = ax[0].imshow(
	# 		Rse,
	# 		extent = [0, x.max(), 0, y.max()],
	# 		origin = 'lower',
	# 		vmin = 0,
	# 		vmax = 2
	# 	)
	# 	cb = fig.colorbar(im1, ax = ax[0],
	# 					 orientation="horizontal",fraction=0.068,anchor=(1.0,0.0), pad = 0.01)
	# 	cb.set_label('$[H_{2}O]$  $(mg/cm^3)$')
	# 	ax[0].set_title('Water Map')
	# 	ax[0].axis('off')


	# 	im2 = ax[1].imshow(
	# 		avgRef,
	# 		extent = [0, x.max(), 0, y.max()],
	# 		origin = 'lower',
	# 		vmin = 0
	# 	)
	# 	cb = plt.colorbar(im2, ax = ax[1],
	# 					 orientation="horizontal",fraction=0.068,anchor=(1.0,0.0), pad = 0.01)
	# 	cb.set_label('Reflectance')
	# 	ax[1].set_title('Avg Reflectance')
	# 	plt.axis('off')
	# 	scalebar = ScaleBar(
	# 		dx = 1e-3,
	# 		location = 'lower right',
	# 		color = [1, 1, 1],
	# 		box_alpha = 0
	# 	)
	# 	ax[1].add_artist(scalebar)
	# 	plt.tight_layout()
	# 	plt.show()
