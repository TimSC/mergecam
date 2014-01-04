from PySide import QtGui, QtCore
import time, vidoutput, vidwriter, videolive

class GuiPanorama(QtGui.QFrame):

	def __init__(self, correspondenceModel, cameraArrangement):
		QtGui.QFrame.__init__(self)

		self.framesRcvSinceOutput = set()
		self.correspondenceModel = correspondenceModel
		self.cameraArrangement = cameraArrangement
		self.currentFrame = {}
		self.currentMeta = {}
		self.visobj = None

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

		self.vidOutStreamWidget = vidoutput.VideoOutWidget("/dev/video0", self.outStreamsManager)
		self.outputBar.addWidget(self.vidOutStreamWidget)
		
		self.vidOutStreamWidget = vidwriter.VideoWriterWidget(self.outFilesManager)
		self.outputBar.addWidget(self.vidOutStreamWidget)
		
	def SetFrame(self, frame, meta):

		#Update GUI with new frame
		if meta['format'] == "RGB24":
			self.scene.clear()
			im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
			pix = QtGui.QPixmap(im2)

			gpm = QtGui.QGraphicsPixmapItem(pix)
			self.scene.addItem(gpm)

	def SetVisObject(self, visobj):
		self.visobj = visobj

	def ProcessFrame(self, frame, meta, devName):
		if devName not in self.correspondenceModel.devInputs: return
		self.currentFrame[devName] = frame
		self.currentMeta[devName] = meta

		if self.visobj is None: return

		if devName in self.framesRcvSinceOutput:
			#We have received this frame again; it is time to write output

			if self.cameraArrangement is not None:
				if 0:
					visobj = visualise.VisualiseArrangement()
					vis = visobj.Vis(self.currentFrame.values(), self.currentMeta.values(), self.framePairs[0], self.cameraArrangement)
					metaOut = {'width': vis.size[0], 'height': vis.size[1], 'format': 'RGB24'}
					self.outBuffer.append([vis.tostring(), metaOut])
				if 1:
					#print len(self.currentFrame), self.currentMeta
					startTime = time.time()
					visPixOut, visMetaOut = self.visobj.Vis(self.currentFrame.values(), self.currentMeta.values())
					print "Generated panorama in",time.time()-startTime,"sec"
					#self.visobj.Vis(self.currentFrame.values(), self.currentMeta.values())

					#visPixOut = bytearray([128 for i in range(800 * 600 * 3)])
					#visMetaOut = {"height": 600, "width": 800, "format": "RGB24"}
					
					#print len(visPixOut), visMetaOut
					#self.outBuffer.append([bytearray(visPixOut), visMetaOut])
					self.SetFrame(bytearray(visPixOut), visMetaOut)

			self.framesRcvSinceOutput = set()

		self.framesRcvSinceOutput.add(devName)

