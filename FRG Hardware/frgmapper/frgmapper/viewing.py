import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib_scalebar.scalebar import ScaleBar
import h5py

# def buildDataframe(filepath):
# 	with h5py.File(filepath, 'r') as f:
# 		data = {
# 			'notes': f['info']['notes'][:],
# 			'laserpower': f['settings']['laserpower'][:],
# 			'suns': f['settings']['suns'][:],
# 			'v': f['data']['v'][:],
# 			'i': f['data']['i'][:],    
# 			'temp': f['data']['temp'][:],
# 			'img': [f['data']['image'][x,:,:] for x in range(f['data']['image'].shape[0])]
# 		}
		
# 	df = pd.DataFrame(data)
# 	return df

# def listMeas(filepath):
# 	with h5py.File(filepath, 'r') as f:
# 		data = {
# 			'notes': f['info']['notes'][:],
# 			'laserpower': f['settings']['laserpower'][:],
# 			'suns': f['settings']['suns'][:],
# 			'v': f['data']['v'][:],
# 			'i': f['data']['i'][:],    
# 			'temp': f['data']['temp'][:],
# 			'img': [f['data']['image'][x,:,:] for x in range(f['data']['image'].shape[0])]
# 		}

# 	for i in range(len(data['v'])):
# 		print('{0}: {1:.3f} V\t{2:.3f} lp\t{3}'.format(i, data['v'][i], data['laserpower'][i], data['notes'][i].decode('utf-8')))

def plotMeas(filepath, index):
	with h5py.File(filepath, 'r') as f:
		avgRef = f['data']['reflectance'][()].mean(axis = 2)	#image to be plotted
		x = f['data']['x'][()]
		y = f['data']['y'][()]
		title = f['info']['name'][()].decode('utf-8')

	fig, ax = plt.subplots(1,1)

	img = avgRef
	# img[img < 0] = 0
	im = ax.imshow(img, extent = [x[0], x[-1], y[-1], y[0]])
	cb = plt.colorbar(im, ax = ax)
	cb.set_label('Average Reflectance (%)')

	sb = ScaleBar(1e-3,
		color = [1,1,1],
		box_alpha = 0,
		location = 'lower right'
		)
	ax.add_artist(sb)

	# add text to plot
	# offset = 0.05
	# startingoffset = 0.02
	# ax.text(
	# 	startingoffset,
	# 	1-startingoffset,
	# 	'{0} V'.format(v),
	# 	transform = ax.transAxes,
	# 	color = [1,1,1],
	# 	verticalalignment = 'top'
	# 	)
	# ax.text(
	# 	startingoffset,
	# 	1 - startingoffset - offset,
	# 	'{0} mA'.format(i),
	# 	transform = ax.transAxes,
	# 	color = [1,1,1],
	# 	verticalalignment = 'top'
	# 	)
	# ax.text(
	# 	startingoffset,
	# 	1 - startingoffset - 2*offset,
	# 	'{0}{1}'.format(lightval, lightunit),
	# 	transform = ax.transAxes,
	# 	color = [1,1,1],
	# 	verticalalignment = 'top'
	# 	)
	# ax.text(
	# 	startingoffset,
	# 	1 - startingoffset - 3*offset,
	# 	'{0} C'.format(t),
	# 	transform = ax.transAxes,
	# 	color = [1,1,1],
	# 	verticalalignment = 'top'
	# 	)
	plt.axis('off')
	plt.title(title)

	plt.show()


