import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib_scalebar.scalebar import ScaleBar
import h5py
from os.path import expanduser
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# import time
root = 'D:\\frgmapper'
# root = 'G:\\My Drive\\FRG\\Projects\\PVRD2 WaRM\\Experiments\\Damp Heat Cell Degradation Testing\\Round 2\\Data'

def plotMeas(filepath, ax = None):
	with h5py.File(filepath, 'r') as f:
		avgRef = f['data']['reflectance'][()].mean(axis = 2)	#image to be plotted
		x = f['data']['x'][()]
		y = f['data']['y'][()]
		title = f['info']['name'][()].decode('utf-8')

	showlater = False
	if ax is None:
		showlater = True
		fig, ax = plt.subplots(1,1)

	img = avgRef
	# img[img < 0] = 0
	im = ax.imshow(img, extent = [x[0], x[-1], y[-1], y[0]], vmin = 0, vmax = np.min([0.4, img.max()]))
	cb = plt.colorbar(im, ax = ax, fraction = 0.046)
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
	ax.set_xticks([])
	ax.set_yticks([])

	if showlater:
		plt.show()

def plotScanLine(self, filepath, ax = None):
	showlater = False
	if ax is None:
		showlater = True
		fig, ax = plt.subplots(1,1)


	with h5py.File(filepath, 'r') as d:
		axis = d['settings']['axis'][()].decode('utf-8')
		x = d['data']['x'][()]
		y = d['data']['y'][()]
		reflectance = d['data']['reflectance'][()]
		label = d['info']['name'][()].decode('utf-8')

	if axis == 'x':
		ax.plot(x, 100*reflectance.mean(axis = 1))
		ax.set_title('{0}\n y = {1}'.format(label, y[0]))
	else:
		ax.plot(y, 100*reflectance.mean(axis = 1))
		ax.set_title('{0}\n x = {1}'.format(label, x[0]))

	ax.set_ylabel('Reflectance (%)')
	ax.set_xlabel('{0} (mm)'.format(axis))

	if showlater:
		plt.show()

def Viewer(directory = root):
	class App(QApplication):
		def __init__(self):
			super().__init__([])
			self.setStyle('Fusion')
			self.window = QWidget()

			self.buildFileBrowser()
			self.scanInfo = self.ScanInfo(self.fileBrowser)
			self.plotCanvas = self.PlotCanvas()
			self.toolbar = NavigationToolbar(self.plotCanvas, self.window)

			# put widgets together into layout
			self.layout = QGridLayout()	
			self.layout.addWidget(self.fileBrowser, 0, 0, 5, 5)
			self.layout.addWidget(self.scanInfo.groupBox, 5, 0, 5, 5)
			self.layout.addWidget(self.plotCanvas, 0, 5, 8, 10)
			self.layout.addWidget(self.toolbar, 8, 5, 2, 10)

			#add layout to window, execute
			self.window.setLayout(self.layout)
			self.window.show()

			# connect actions
			self.fileBrowser.clicked.connect(self.update)
		
		def buildFileBrowser(self, root = root):
			model = QFileSystemModel()
			model.setRootPath(root)
			self.fileBrowser = QTreeView()
			self.fileBrowser.setModel(model)
			self.fileBrowser.setRootIndex(model.index(directory))	
		
		def update(self):
			index = self.fileBrowser.selectedIndexes()[0]
			self.currentFilepath = self.fileBrowser.model().filePath(index)

			if self.currentFilepath[-3:] == '.h5':
				with h5py.File(self.currentFilepath, 'r') as d:
					self.scanInfo.label.setText(d['info']['name'][()].decode('utf-8'))
					x = d['data']['x'][()]
					y = d['data']['y'][()]
					xsize = x.max() - x.min()
					ysize = y.max() - y.min()
					scanType = d['info']['type'][()].decode('utf-8')
					self.scanInfo.dimensions.setText('{0} mm x {1} mm'.format(xsize, ysize))
					if 'fits' in d.keys():
						fitted = 'True'
					else:
						fitted = 'False'

					self.scanInfo.fitted.setText(fitted)

				self.plotCanvas.reset()
				if scanType in ['scanArea', 'scanAreaWaRD']:
					plotMeas(filepath = self.currentFilepath, ax = self.plotCanvas.ax)
				elif scanType == 'scanLine':
					plotScanLine(filepath = self.currentFilepath, ax = self.plotCanvas.ax)
				self.plotCanvas.draw()


		class ScanInfo():
			def __init__(self, fileBrowser):
				self.groupBox = QGroupBox("Scan Info")

				vbox = QGridLayout()
				for idx, l in enumerate(['Label:', 'Dimensions:', 'Fitted:']):
					vbox.addWidget(QLabel(l), idx, 0)

				self.label = QLabel(' ')
				self.dimensions = QLabel(' ')
				self.fitted = QLabel(' ')

				for idx, r in enumerate([self.label, self.dimensions, self.fitted]):
					vbox.addWidget(r, idx, 1)

				self.groupBox.setLayout(vbox)					
		
		class PlotCanvas(FigureCanvas):
			def __init__(self, parent=None, width=5, height=4, dpi=100):
				self.fig = plt.figure(dpi=dpi)
				self.ax = self.fig.add_subplot(111)

				FigureCanvas.__init__(self, self.fig)
				self.setParent(parent)

				FigureCanvas.setSizePolicy(self,
						QSizePolicy.Expanding,
						QSizePolicy.Expanding)
				FigureCanvas.updateGeometry(self)

			def reset(self):
				self.fig.clear()
				self.ax = self.fig.add_subplot(111)


	app = App()
	app.exec_()



