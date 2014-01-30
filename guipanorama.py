from PySide import QtGui, QtCore
import time, vidoutput, vidwriter, videolive, config, math, copy, sys
import scipy.misc as misc
import numpy as np

class PanoGraphicsView(QtGui.QGraphicsView):
	viewMoved = QtCore.Signal(float, float)

	def __init__(self, scene = None):
		QtGui.QGraphicsView.__init__(self, scene)
		self.proj = None
		self.prevMousePos = None
		self.staticProj = None

	def mousePressEvent(self, event):
		try:
			return self.ProcessMousePress(event)
		except Exception as err:
			print err

	def ProcessMousePress(self, event):

		if self.proj is None: return
		self.staticProj = self.proj
		mousePos = event.pos()
		posx = mousePos.x()
		posy = mousePos.y()
		self.prevMousePos = self.staticProj.UnProj([(posx, posy)])[0]

	def mouseMoveEvent(self, event):
		try:
			return self.ProcessMouseMove(event)
		except Exception as err:
			print err

	def ProcessMouseMove(self, event):
		if self.staticProj is None: return
		if self.prevMousePos is None: return

		mousePos = event.pos()
		posx = mousePos.x()
		posy = mousePos.y()
		mouseLatLon = self.staticProj.UnProj([(posx, posy)])[0]
		
		shift = (mouseLatLon[0] - self.prevMousePos[0], mouseLatLon[1] - self.prevMousePos[1])
		self.prevMousePos = mouseLatLon
		self.viewMoved.emit(shift[0], shift[1])

	def mouseReleaseEvent(self, event):
		try:
			self.staticProj = None
		except Exception as err:
			print err

	def SetProj(self, proj):
		self.proj = proj

class GuiPanorama(QtGui.QFrame):

	viewParametersChanged = QtCore.Signal()

	def __init__(self):
		QtGui.QFrame.__init__(self)

		self.framesRcvSinceOutput = set()
		self.currentFrame = []
		self.currentMeta = []
		self.visObj = None
		self.activeCams = []
		self.fullVersion = config.FULL_VERSION
		self.watermark = None
		self.blend = False
		self.autoBright = True
		self.outw = 640
		self.outh = 480
		self.cLat = 0.
		self.cLon = 0.
		self.hfov = math.radians(360.0)
		self.vfov = math.radians(180.0)

		self.outStreamsManager = videolive.Video_out_stream_manager()
		self.outFilesManager = videolive.Video_out_file_manager()

		self.layout = QtGui.QVBoxLayout()
		self.setLayout(self.layout)

		self.scene = QtGui.QGraphicsScene()
		self.view = PanoGraphicsView(self.scene)
		self.view.viewMoved.connect(self.ViewMoved)
		self.layout.addWidget(self.view, 1)

		#Output bar
		self.outputBar = QtGui.QHBoxLayout()
		self.layout.addLayout(self.outputBar)
				
		self.controlButtons = QtGui.QVBoxLayout()
		self.outputBar.addLayout(self.controlButtons)

		self.configure = QtGui.QPushButton("Configure View")
		self.configure.pressed.connect(self.ConfigurePressed)
		self.controlButtons.addWidget(self.configure)

		self.zoomInButton = QtGui.QPushButton("Zoom In")
		self.zoomInButton.pressed.connect(self.ZoomInPressed)
		self.controlButtons.addWidget(self.zoomInButton)	

		self.zoomOutButton = QtGui.QPushButton("Zoom Out")
		self.zoomOutButton.pressed.connect(self.ZoomOutPressed)
		self.controlButtons.addWidget(self.zoomOutButton)	

		self.vidOutStreamWidget = vidoutput.VideoOutWidget(self.outStreamsManager)
		self.outputBar.addWidget(self.vidOutStreamWidget)
		
		self.vidOutFileWidget = vidwriter.VideoWriterWidget(self.outFilesManager, self.fullVersion)
		self.outputBar.addWidget(self.vidOutFileWidget)
		
	def SetFrame(self, frame, meta):

		#Update GUI with new frame
		if meta['format'] == "RGB24":
			self.scene.clear()
			self.scene.setSceneRect(0, 0, meta['width'], meta['height'])

			#Add merged image to scene
			im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
			pix = QtGui.QPixmap(im2)

			gpm = QtGui.QGraphicsPixmapItem(pix)
			self.scene.addItem(gpm)

			#Watermark
			if not self.fullVersion:
				logoSize = int(round(meta['width'] * 0.08))
				if self.watermark is None:					
					logo = QtGui.QImage("resources/Kinatomic-Logo-Square-whitebackground300.png")
					logo = logo.scaled(logoSize,logoSize)
					self.watermark = QtGui.QPixmap(logo)
				wm = QtGui.QGraphicsPixmapItem(self.watermark)
				wm.setOffset(meta['width']-2*logoSize, meta['height']-2*logoSize)
				self.scene.addItem(wm)

	def SetVisObject(self, visobj, outProj):
		self.visObj = visobj
		self.view.SetProj(outProj)

		#Update visualisation sizes
		if outProj is not None:
			w = outProj.imgW
			h = outProj.imgH
			self.vidOutStreamWidget.VideoSizeChanged(w, h)
			self.vidOutFileWidget.VideoSizeChanged(w, h)

	def FrameGenerated(self, frame, meta):
		self.SetFrame(frame, meta)
		self.vidOutStreamWidget.SendFrame(frame, meta, "pano")
		self.vidOutFileWidget.SendFrame(frame, meta, "pano")

	def ProcessFrame(self, frame, meta, devName):
		
		ind = None
		#print "ProcessFrame", devName
		for i, devInfo in enumerate(self.activeCams):
			if devName == devInfo[0]:
				ind = i
				break
		#if ind is None: print ind, self.activeCams

		if ind is None: return
		while len(self.currentFrame) < len(self.activeCams): self.currentFrame.append(None)
		while len(self.currentMeta) < len(self.activeCams): self.currentMeta.append(None)
		
		self.currentFrame[ind] = frame
		self.currentMeta[ind] = meta

		if self.visObj is None: return

		if devName in self.framesRcvSinceOutput:
			#We have received this frame again; it is time to write output
	
			if 0:
				#Save input images
				for i, (frame, meta) in enumerate(zip(self.currentFrame,self.currentMeta)):
					if frame is None:
						continue
					img = np.fromstring(str(frame), np.uint8, meta['width'] * meta['height'] * 3)
					img = img.reshape((meta['height'], meta['width'], 3))
					print img.shape
					misc.imsave("test{0}.png".format(i), img)

			if 1:
				#print len(self.currentFrame), self.currentMeta
				startTime = time.time()

				#print sys.gettotalrefcount()
				
				self.visObj.SetSmoothBlending(self.blend)
				self.visObj.SetAutoBright(self.autoBright)
				visPixOut, visMetaOut = self.visObj.Vis(self.currentFrame, self.currentMeta)
				print "Generated panorama in",time.time()-startTime,"sec"
				#self.visObj.Vis(self.currentFrame, self.currentMeta)
			if 1:
				#visPixOut = bytearray([128 for i in range(800 * 600 * 3)])
				#visMetaOut = {"height": 600, "width": 800, "format": "RGB24"}
					
				#print len(visPixOut), visMetaOut
				#self.outBuffer.append([bytearray(visPixOut), visMetaOut])
				self.FrameGenerated(bytearray(visPixOut), visMetaOut)

			self.framesRcvSinceOutput = set()

		self.framesRcvSinceOutput.add(devName)

	def SetActiveCams(self, activeCams):
		print "SetActiveCams", activeCams
		self.activeCams = activeCams

	def OutputChangeSizePressed(self, w, h):
		self.outw = w
		self.outh = h
		self.viewParametersChanged.emit()
		self.watermark = None

	def GetOutputSize(self):
		return self.outw, self.outh

	def ConfigurePressed(self):
		try:
			dlg = ConfigDialog(self, config.FULL_VERSION)
			dlg.outputSizeChanged.connect(self.OutputChangeSizePressed)
			dlg.SetSmoothBlend(self.blend)
			dlg.SetAutoBright(self.autoBright)
			dlg.SetOutputSize(self.outw, self.outh)
			dlg.exec_()
			self.blend = dlg.GetSmoothBlend()
			self.autoBright = dlg.GetAutoBright()
			self.outw, self.outh = dlg.GetOutputSize()
		except Exception as err:
			print err

	def GetViewCentre(self):
		return self.cLat, self.cLon

	def GetFov(self):
		return self.hfov, self.vfov

	def ZoomInPressed(self):
		try:
			print "zoom in"
			self.hfov /= 2.
			self.vfov /= 2.
			self.viewParametersChanged.emit()
		except Exception as err:
			print err
	
	def ZoomOutPressed(self):
		try:
			print "zoom out"
			self.hfov *= 2.
			self.vfov *= 2.
			self.viewParametersChanged.emit()
		except Exception as err:
			print err

	def ViewMoved(self, dLat, dLon):
		try:
			#print dLat, dLon, self.cLat, self.cLon
			self.cLat -= dLat
			self.cLon -= dLon
			self.viewParametersChanged.emit()
		except Exception as err:
			print err

# ***************************************************************

class ConfigDialog(QtGui.QDialog):

	outputSizeChanged = QtCore.Signal(int, int)

	def __init__(self, parent = None, fullVersion = 0):
		QtGui.QDialog.__init__(self, parent)

		self.setWindowTitle('PanoView')
		self.setMinimumWidth(500)

		self.mainLayout = QtGui.QVBoxLayout()
		self.setLayout(self.mainLayout)
		
		self.mainLayout.addWidget(QtGui.QLabel("Output Size"))

		self.outsizeLayout = QtGui.QVBoxLayout()
		self.mainLayout.addLayout(self.outsizeLayout)

		self.allowedSizes = [480, 640, 800, 1024, 1200, 1600, 2048]

		self.widthLabelAndCombo = QtGui.QHBoxLayout()
		self.outsizeLayout.addLayout(self.widthLabelAndCombo)	
		self.heightLabelAndCombo = QtGui.QHBoxLayout()
		self.outsizeLayout.addLayout(self.heightLabelAndCombo)	

		self.outputSizeWCombo = QtGui.QComboBox()
		for si in self.allowedSizes:
			self.outputSizeWCombo.addItem(str(si))

		self.outputSizeWCombo.setEnabled(fullVersion)
		self.widthLabelAndCombo.addWidget(QtGui.QLabel("Width:"))	
		self.widthLabelAndCombo.addWidget(self.outputSizeWCombo)	

		self.outputSizeHCombo = QtGui.QComboBox()
		for si in self.allowedSizes:
			self.outputSizeHCombo.addItem(str(si))

		self.outputSizeHCombo.setEnabled(fullVersion)
		self.heightLabelAndCombo.addWidget(QtGui.QLabel("Height:"))	
		self.heightLabelAndCombo.addWidget(self.outputSizeHCombo)	

		self.outputSizeChangeButton = QtGui.QPushButton("Change")
		self.outsizeLayout.addWidget(self.outputSizeChangeButton)
		self.outputSizeChangeButton.pressed.connect(self.OutputChangeSizePressed)
		self.outputSizeChangeButton.setEnabled(fullVersion)

		if not fullVersion:
			self.purchaseButton = QtGui.QPushButton("Purchase PRO Version to Increase Size")
			self.mainLayout.addWidget(self.purchaseButton)
			self.purchaseButton.pressed.connect(self.PurchasePressed)
		else:
			self.purchaseButton = None

		self.blendLayout = QtGui.QHBoxLayout()
		self.mainLayout.addLayout(self.blendLayout)

		self.blendCheckBox = QtGui.QCheckBox()
		self.blendLayout.addWidget(self.blendCheckBox)
	
		self.blendLabel = QtGui.QLabel("Smooth Blend")
		self.blendLayout.addWidget(self.blendLabel)

		self.autoBrightLayout = QtGui.QHBoxLayout()
		self.mainLayout.addLayout(self.autoBrightLayout)

		self.autoBrightCheckBox = QtGui.QCheckBox()
		self.autoBrightLayout.addWidget(self.autoBrightCheckBox)
	
		self.autoBrightLabel = QtGui.QLabel("Automatically Match Brightness")
		self.autoBrightLayout.addWidget(self.autoBrightLabel)

		self.closeButton = QtGui.QPushButton("Close")
		self.mainLayout.addWidget(self.closeButton)
		self.closeButton.pressed.connect(self.close)
	
	def SetOutputSize(self, w, h):
		if w in self.allowedSizes:
			wi = self.allowedSizes.index(w)
			self.outputSizeWCombo.setCurrentIndex(wi)
		if h in self.allowedSizes:
			hi = self.allowedSizes.index(h)
			self.outputSizeHCombo.setCurrentIndex(hi)

	def GetOutputSize(self):
		return int(self.outputSizeWCombo.currentText()), int(self.outputSizeHCombo.currentText())

	def OutputChangeSizePressed(self):
		outw = int(self.outputSizeWCombo.currentText())
		outh = int(self.outputSizeHCombo.currentText())

		self.outputSizeChanged.emit(outw, outh)

	def PurchasePressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.REGISTER_URL))

	def SetSmoothBlend(self, val):
		self.blendCheckBox.setChecked(val)

	def GetSmoothBlend(self):
		return self.blendCheckBox.isChecked()

	def SetAutoBright(self, val):
		self.autoBrightCheckBox.setChecked(val)

	def GetAutoBright(self):
		return self.autoBrightCheckBox.isChecked()