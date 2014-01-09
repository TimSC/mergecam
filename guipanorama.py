from PySide import QtGui, QtCore
import time, vidoutput, vidwriter, videolive

class GuiPanorama(QtGui.QFrame):

	def __init__(self):
		QtGui.QFrame.__init__(self)

		self.framesRcvSinceOutput = set()
		self.currentFrame = []
		self.currentMeta = []
		self.visObj = None
		self.activeCams = []

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

