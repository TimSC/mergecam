from PySide import QtGui, QtCore
import time, vidoutput, vidwriter, videolive
import scipy.misc as misc
import numpy as np

class GuiPanorama(QtGui.QFrame):

	outputSizeChanged = QtCore.Signal(int, int)

	def __init__(self):
		QtGui.QFrame.__init__(self)

		self.framesRcvSinceOutput = set()
		self.currentFrame = []
		self.currentMeta = []
		self.visObj = None
		self.activeCams = []
		self.fullVersion = True

		self.outStreamsManager = videolive.Video_out_stream_manager()
		self.outFilesManager = videolive.Video_out_file_manager()

		self.layout = QtGui.QVBoxLayout()
		self.setLayout(self.layout)

		self.scene = QtGui.QGraphicsScene()
		self.view = QtGui.QGraphicsView(self.scene)
		self.layout.addWidget(self.view, 1)

		#Output bar
		self.outputBar = QtGui.QHBoxLayout()
		self.layout.addLayout(self.outputBar)

		self.sizeAndRegisterLayout = QtGui.QVBoxLayout()
		self.outputBar.addLayout(self.sizeAndRegisterLayout)
		self.sizeAndRegisterLayout.addWidget(QtGui.QLabel("Output Size"))

		self.outsizeLayout = QtGui.QHBoxLayout()
		self.sizeAndRegisterLayout.addLayout(self.outsizeLayout)

		self.outputSizeWCombo = QtGui.QComboBox()
		self.outputSizeWCombo.addItem("480")
		self.outputSizeWCombo.addItem("640")
		self.outputSizeWCombo.addItem("800")
		self.outputSizeWCombo.addItem("1024")
		self.outputSizeWCombo.setCurrentIndex(1)
		self.outputSizeWCombo.setEnabled(self.fullVersion)
		self.outsizeLayout.addWidget(self.outputSizeWCombo)	

		self.outputSizeHCombo = QtGui.QComboBox()
		self.outputSizeHCombo.addItem("480")
		self.outputSizeHCombo.addItem("640")
		self.outputSizeHCombo.addItem("800")
		self.outputSizeHCombo.addItem("1024")
		self.outputSizeHCombo.setCurrentIndex(0)
		self.outputSizeHCombo.setEnabled(self.fullVersion)
		self.outsizeLayout.addWidget(self.outputSizeHCombo)	

		self.outputSizeChangeButton = QtGui.QPushButton("Change")
		self.outsizeLayout.addWidget(self.outputSizeChangeButton)
		self.outputSizeChangeButton.pressed.connect(self.OutputChangeSizePressed)
		self.outputSizeChangeButton.setEnabled(self.fullVersion)

		if not self.fullVersion:
			self.purchaseButton = QtGui.QPushButton("Purchase PRO Version to Increase Size")
			self.sizeAndRegisterLayout.addWidget(self.purchaseButton)
			self.purchaseButton.pressed.connect(self.PurchasePressed)
		else:
			self.purchaseButton = None

		self.vidOutStreamWidget = vidoutput.VideoOutWidget(self.outStreamsManager)
		self.outputBar.addWidget(self.vidOutStreamWidget)
		
		self.vidOutFileWidget = vidwriter.VideoWriterWidget(self.outFilesManager)
		self.outputBar.addWidget(self.vidOutFileWidget)
		
	def SetFrame(self, frame, meta):

		#Update GUI with new frame
		if meta['format'] == "RGB24":
			self.scene.clear()
			im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
			pix = QtGui.QPixmap(im2)

			gpm = QtGui.QGraphicsPixmapItem(pix)
			self.scene.addItem(gpm)

	def SetVisObject(self, visobj):
		self.visObj = visobj

		#Update visualisation sizes
		


	def FrameGenerated(self, frame, meta):
		self.SetFrame(frame, meta)
		self.vidOutStreamWidget.SendFrame(frame, meta, "pano")
		self.vidOutFileWidget.SendFrame(frame, meta, "pano")
		pass

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

	def OutputChangeSizePressed(self):
		outw = int(self.outputSizeWCombo.currentText())
		outh = int(self.outputSizeHCombo.currentText())

		self.outputSizeChanged.emit(outw, outh)

	def PurchasePressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://www.kinatomic.com/"))

	def GetOutputSize(self):
		outw = int(self.outputSizeWCombo.currentText())
		outh = int(self.outputSizeHCombo.currentText())
		return outw, outh
