#  to run, type import frgpl.checkPLmaps
import h5py
import matplotlib.pyplot as plt
import os

def plotall():

	folder='C:\\Users\\Operator\\Desktop\\frgPL\\PVRD2 Degradation Study\\20191121'
	#folder='C:\\Users\\Operator\\Desktop\\frgPL\\PVRD2 Degradation Study\\20191119'

	plt.ion()

	for root,dirn,o in os.walk(folder):
		for filen in o:
			file=os.path.join(folder,filen)
			hf=h5py.File(file,'r')
			plt.figure()
			k=0
			for n in range(30,55):
				k=k+1
				v=hf['data']['v'][n]
				plt.subplot(5,5,k).set_title('v= {}'.format(v))
				plt.imshow(hf['data']['image'][n])
				plt.colorbar()
			hf.close()

	#import matplotlib.pyplot as plt
	#plt.close('all')

def plotPL(filepath):
	#idx=[b'open circuit PL image' in x for x in hf['settings']['notes'][()]]
	#vmeas=d['data']['v'][()][idx]

	plt.ion()

	hf=h5py.File(filepath,'r')
	idxPLIV=[b'PLIV' in x for x in hf['settings']['notes'][()]] # list of indices to PLIV images
	idxEL=[b'part of Rse measurement series' in x for x in hf['settings']['notes'][()]]
	PLIVdata=hf['data']['image'][()][idxPLIV]# array containing PLIV maps
	PLIVvolt=hf['data']['v'][()][idxPLIV]#
	ELdata=hf['data']['image'][()][idxEL]# array containing PLIV maps
	ELvolt=hf['data']['v'][()][idxEL]#

	plt.figure()
	k=0
	for v,im in zip(PLIVvolt,PLIVdata):
		k=k+1
		plt.subplot(6,6,k).set_title('v= {}'.format(v))
		plt.imshow(im)
		plt.colorbar()
	hf.close()