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
import scipy.linalg as la
import threading
from matplotlib.widgets import Button
from scipy.optimize import lsq_linear
import multiprocessing as mp




def fitRsEL(file, area = 24.01, plot = False):
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
		
		#throw away the first five points, give a more linear calibration constant fit.
		points_to_exclude = 5
		exclude = 0
		for i in range(len(idx)):
			if idx[i] == True:
				idx[i] == False
			if exclude >= points_to_exclude:
				break


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
	with h5py.File(file, 'a') as d:
		if 'fits' in d.keys():
			fits = d['fits']
		else:
			fits = d.create_group('/fits')

		_fillDataset(d['fits'], 'Rs_EL', Rse, 'Local series resistance (ohm*cm^2) calculated by fitting electroluminescence data.')
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

def fitPLIV(fpath, area = 24.01):
	#define constants
	k = 1.38e-23 #J/K
	qC = 1.6022e-19 #C
	T = 298.14 #K
	Vt = k*T/qC
	area = area #working in cm2

	###load PLIV data
	with h5py.File(fpath, 'r') as d:
		idx = [i for i, x in enumerate(d['settings']['notes'][()]) if b'PLIV' in x]
		measCurr = -d['data']['i'][idx] #solar cell convention
		measVolt = d['data']['v'][idx] 
		imgs = d['data']['image_bgc'][idx]
		suns = d['settings']['suns'][idx]
		setVolt = d['settings']['vbias'][idx]

	# imgs[imgs<=0] = 1e-4	#avoid breaking log functions down the road
	#locate short-circuit PL images per laser intensity to use for background subtraction
	correctionImgs = {}
	correctionJscs = {}
	dataIdx = []
	for suns_, setVolt_, img_, measCurr_ in zip(suns, setVolt, imgs, measCurr):
		if setVolt_ == 0:
			correctionImgs[suns_] = img_.copy()
			correctionJscs[suns_] = measCurr_/area
			dataIdx.append(False)
		elif setVolt_ <= 0.55 and suns_ <= 0.4: #images with low luminescence add noise, dont affect fits (especiall since shunt is ignored)
			dataIdx.append(False)
		else:
			dataIdx.append(True)
	#### remove background from all images, find Voc and Mpp 1 sun images. discard correction images from the dataset		
	for idx, suns_ in enumerate(suns):
	    imgs[idx] = imgs[idx] - correctionImgs[suns_] #remove baseline counts from longpass filter leakage, etc.
	imgs[imgs<=0] = 1e-4	#avoid breaking log functions down the road

	# find Voc image
	imgVoc = imgs[0].copy()
	
	# find MPP image
	allSetVolts = np.unique(setVolt)
	allSetVolts.sort()
	mppVolt = allSetVolts[1] #second value of sorted list of bias voltages (first value = 0 for short circuit images)
	allmppIdx = np.where(setVolt == mppVolt)
	oneSunIdx = np.where(suns == suns.max()) #max should be 1 sun, but in some cases PLIV hardware can only reach ~= 1 sun (0.98 suns, etc). 
	mppIdx = np.intersect1d(allmppIdx, oneSunIdx)[0]
	imgMPP = imgs[mppIdx].copy()
	voltMPP = measVolt[mppIdx].copy()

	# throw away short circuit images
	imgs = imgs[dataIdx]
	measCurr = measCurr[dataIdx]
	measVolt = measVolt[dataIdx]
	suns = suns[dataIdx]
	setVolt = setVolt[dataIdx]

	###generate matrix to solve PLIV. 
	#matrix 1: p x q x numimages x 4 (unity, Jsc (A/m2), Photon flux Phi (PL - short-circuit counts), sqrt(Phi))
	#matrix 2: p x q x numimages x 1 (Vthermal * log(Phi) - Vterminal)
	M = np.ones((imgs.shape[1], imgs.shape[2], imgs.shape[0], 4))
	N = np.ones((imgs.shape[1], imgs.shape[2], imgs.shape[0]))
	for idx, img_, suns_, measV_, measC_, setV_ in zip(range(suns.shape[0]), imgs, suns, measVolt, measCurr, setVolt):
		M[:,:,idx,1] = correctionJscs[suns_]
		# img_[img_<= 0] = 0
		M[:,:,idx,2] = -img_
		M[:,:,idx,3] = -np.sqrt(img_)
		# img_[img_<= 0] = 1e-20
		N[:,:,idx] = Vt * np.log(img_) - measV_

	# solve matrix, process into each fit
	x = np.full((imgs.shape[1], imgs.shape[2], 4), np.nan)

	bounds = [
            [-np.inf, 0, 0, 0],
            [np.inf, np.inf, np.inf, np.inf]
            ] #C, Rs, J01, J02
	for p,q in tqdm(np.ndindex(imgs[0].shape), total = imgs[0].ravel().shape[0]):
		x[p,q] = lsq_linear(M[p,q], N[p,q], bounds = bounds)['x']
		# Q,R,perm = la.qr(M[p,q], pivoting = True)
		# print(perm)
		# Qb = np.matmul(Q.T, N[p,q])
		# x[p,q] = np.linalg.lstsq(R, Qb, rcond = None)[0]
		# print(x[p,q].shape)
		# x[p,q] = x[p,q][perm]


	C = np.exp(x[:,:,0]/Vt)
	Rs = x[:,:,1]	#ohm cm^2
	J01 = x[:,:,2]*C/Rs
	J02 = x[:,:,3]*np.sqrt(C)/Rs

	Voc1sun = Vt*np.log(imgVoc/C)
	Vmpp1sun = Vt*np.log(imgMPP/C)

	Jmpp1sun = -J01*(np.exp(Vmpp1sun/Vt) - 1) - J02*(np.exp(Vmpp1sun/(2*Vt))-1) + correctionJscs[suns.max()]
	FF1sun = (voltMPP*Jmpp1sun) / (correctionJscs[suns.max()]*Voc1sun)
	nu1sun = Vmpp1sun*Jmpp1sun / (1e-1)	#divided by incident power, assuming 0.1 W/cm2


	result = {
		'x': x,
		'C': C,
		'Rs': Rs, #ohm cm2
		'J01': J01 * 1e3, #convert A/cm2 -> mA/cm2
		'J02': J02 * 1e3, #convert A/cm2 -> mA/cm2
		'Voc': Voc1sun,
		'Vmpp': Vmpp1sun,
		'Jmpp': Jmpp1sun * 1e3, #convert A/cm2 -> mA/cm2
		'FF': FF1sun * 100, #convert to percent
		'Efficiency': nu1sun * 100, #percent
		'imgVoc': imgVoc,
		'imgMPP': imgMPP
	}

	# for k, v in result.items():
	# 	result[k][v < 0] = np.nan

	# plt.show()

	with h5py.File(fpath, 'a') as d:
		if 'fits' in d.keys():
			fits = d['fits']
		else:
			fits = d.create_group('/fits')

		_fillDataset(d['fits'], 'Rs_PLIV', result['Rs'], 'Local series resistance (ohm*cm^2) calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'J01', result['J01'], 'Local J01 calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'J02', result['J02'], 'Local J02 calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'Voc', result['Voc'], 'Local Voc (V) calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'Vmpp', result['Vmpp'], 'Local Vmpp (V) calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'Jmpp', result['Jmpp'], 'Local Jmpp (mA/cm2) calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'FF', result['FF'], 'Local fill factor calculated by fitting PLIV data.')
		_fillDataset(d['fits'], 'Efficiency', result['Efficiency'], 'Local efficiency calculated by fitting PLIV data.')

		# fillDataset(d['fits'], 'celltype', celltype.encode('utf-8'), 'Cell architecture assumed during fitting.')
		# fillDataset(d['fits'], 'wl_eva', wl_eva, 'Wavelength used as EVA absorbance point.')
		# fillDataset(d['fits'], 'wl_h2o', wl_h2o, 'Wavelength used as water absorbance point.')
		# fillDataset(d['fits'], 'wl_ref', wl_ref, 'Wavelength used as reference absorbance point.')
		# fillDataset(d['fits'], 'poly', [p1, p2], 'Polynomial fit coefficients used to convert absorbances to water content. From highest to lowest order.')
		# fillDataset(d['fits'], 'avgref', avgRef, 'Average reflectance at each point')
	# return result

def ManualRegistrationSelection(file, **kwargs):
	with h5py.File(file, 'a') as d:
		# use average reflectance as reference to pick corners 
		regImg = d['data']['image_bgc'][-2] #Highest Bias + Suns image for corner location
		p = ImagePointPicker(regImg, pts = 4, **kwargs)

		# add points to fits group.
		if 'fits' in d.keys():
			fits = d['fits']
		else:
			fits = d.create_group('fits')

		_fillDataset(d['fits'], 'registrationpoints', p, 'Four corners of cell, used for registration. Points are ordered top right, top left, bottom left, bottom right, assuming that the cell is oriented with the busbar horizontal and closer to the top edge of the cell')

def BatchManualRegistrationSelection(directory, overwrite = False, **kwargs):
	def traverse_files(f, files = [], first = True):
		if first:
			for f_ in tqdm(os.listdir(f)):
				f__ = os.path.join(f, f_)
				if os.path.isdir(f__):
					files = traverse_files(f__, files, first = False)
				else:
					if f__[-3:] == '.h5':
						try:
							with h5py.File(f__, 'r') as d:
								if 'fits/registrationpoints' not in d:
									files.append(f__)
						except:
							pass
		else:
			for f_ in os.listdir(f):
				f__ = os.path.join(f, f_)
				if os.path.isdir(f__):
					files = traverse_files(f__, files, first = False)
				else:
					if f__[-3:] == '.h5':
						try:
							with h5py.File(f__, 'r') as d:
								if 'fits/registrationpoints' not in d:
									files.append(f__)
						except:
							pass			
		return files

	for f in tqdm(traverse_files(directory)):
		try:
			ManualRegistrationSelection(f, **kwargs)
		except:
			print('Error fitting {0}'.format(f))

def loopme(filepath):
		try:
			fitPLIV(filepath)
		except:
			print('Error fitting {0}'.format(filepath))# def BatchManualRegistrationSelection(directory, overwrite = False, **kwargs):

def BatchPLIVFit(directory, overwrite = False):
	def traverse_files(f, files = [], first = True):
		if first:
			for f_ in tqdm(os.listdir(f)):
				f__ = os.path.join(f, f_)
				if os.path.isdir(f__):
					files = traverse_files(f__, files, first = False)
				else:
					if f__[-3:] == '.h5':
						try:
							with h5py.File(f__, 'r') as d:
								if 'fits/registrationpoints' not in d or overwrite == True:
									files.append(f__)
						except:
							pass
		else:
			for f_ in os.listdir(f):
				f__ = os.path.join(f, f_)
				if os.path.isdir(f__):
					files = traverse_files(f__, files, first = False)
				else:
					if f__[-3:] == '.h5':
						try:
							with h5py.File(f__, 'r') as d:
								if 'fits/registrationpoints' not in d or overwrite == True:
									files.append(f__)
						except:
							pass			
		return files

	# for f in tqdm(traverse_files(directory)):
	# 	try:
	# 		fitPLIV(f, **kwargs)
	# 	except:
	# 		print('Error fitting {0}'.format(f))# def BatchManualRegistrationSelection(directory, overwrite = False, **kwargs):
	
	with mp.Pool(mp.cpu_count()) as p:
		p.map(loopme, traverse_files(directory))

# 	class fobject():
# 		def __init__(self, directory = directory):
# 			self.rootdir = directory
# 			self.files = []
		
# 		def traverse_files(self, f = None):
# 			if f is None:
# 				f = self.rootdir
# 			for f_ in tqdm(os.listdir(f)):
# 				f__ = os.path.join(f, f_)
# 				if os.path.isdir(f__):
# 					self.traverse_files(f__)
# 				else:
# 					if f__[-3:] == '.h5':
# 						try:
# 							with h5py.File(f__, 'r') as d:
# 								if not overwrite and 'fits/registrationpoints' not in d:
# 									self.files.append(f__)
# 						except:
# 							pass

# 	fileobject = fobject(directory = directory)
# 	traverse_thread = threading.Thread(target = fileobject.traverse_files)
# 	print('Starting to search for PL data files...')
# 	traverse_thread.start()
	
# 	time.sleep(0.1)

# 	file_idx = 0
# 	startTime = time.time()
# 	while traverse_thread.is_alive() or file_idx < len(fileobject.files):
# 		if file_idx < len(fileobject.files):		
# 			if file_idx > 0:
# 				print('{0}/{1}, {2:.0f} s remaining'.format(file_idx, len(fileobject.files), (time.time()-startTime)*(len(fileobject.files)-file_idx)/file_idx))
# 			try:
# 				ManualRegistrationSelection(fileobject.files[file_idx], **kwargs)
# 			except:
# 				print('Error fitting {0}'.format(fileobject.files[file_idx]))
# 			file_idx += 1
# 		else:
# 			time.sleep(0.2)

## Image registration point picking. Taken from frgtools.imageprocessing
class __ImgPicker():
	def __init__(self, img, pts, markersize = 0.3, **kwargs):
		self.numPoints = pts
		self.currentPoint = 0
		self.finished = False
		self.markersize = markersize

		self.fig, self.ax = plt.subplots()
		self.ax.imshow(img, picker = True, **kwargs)
		self.fig.canvas.mpl_connect('pick_event', self.onpick)

		self.buttonAx = plt.axes([0.4, 0, 0.1, 0.075])
		self.stopButton = Button(self.buttonAx, 'Done')
		self.stopButton.on_clicked(self.setFinished)

		self.pickedPoints = [None for x in range(self.numPoints)]
		self.pointArtists = [None for x in range(self.numPoints)]
		self.pointText = [None for x in range(self.numPoints)]

		plt.show(block = True)        
	
	def setFinished(self, event):
		self.finished = True
		plt.close(self.fig)
	
	def onpick(self, event):
		if not self.finished:
			mevt = event.mouseevent
			idx = self.currentPoint % self.numPoints
			self.currentPoint += 1

			x = mevt.xdata
			y = mevt.ydata
			self.pickedPoints[idx] = [x,y]

			if self.pointArtists[idx] is not None:
				self.pointArtists[idx].remove()
			self.pointArtists[idx] = plt.Circle((x,y), self.markersize, color = [1,1,1])
			self.ax.add_patch(self.pointArtists[idx])

			if self.pointText[idx] is not None:
				self.pointText[idx].set_position((x,y))
			else:
				self.pointText[idx] = self.ax.text(x,y, '{0}'.format(idx), color = [0,0,0], ha = 'center', va = 'center')
				self.ax.add_artist(self.pointText[idx])

			self.fig.canvas.draw()
			self.fig.canvas.flush_events()

def ImagePointPicker(img, pts = 4, **kwargs):
	"""
	Given an image and a number of points, allows the user to interactively select points on the image.
	These points are returned when the "Done" button is pressed. Useful to generate inputs for AffineCalculate.
	"""
	imgpicker = __ImgPicker(img, pts, **kwargs)
	return imgpicker.pickedPoints


## write fits to h5 file
def _fillDataset(d, name, data, description):
	if name in d.keys():
		del d[name]
	temp = d.create_dataset(name, data = data)
	temp.attrs['description'] = description