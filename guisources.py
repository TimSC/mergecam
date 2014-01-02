from PyQt4 import QtGui, QtCore
import videolive, vidinput, vidpano, time

class GuiSources(QtGui.QFrame):
	def __init__(self, devManager):
		QtGui.QFrame.__init__(self)

		

		self.inputDeviceToWidgetDict = {}
		self.processingWidgets = {}
		self.rxTimes = {}
		self.devManager = devManager

		self.selectInputsLayout = QtGui.QHBoxLayout()
		self.setLayout(self.selectInputsLayout)

		#Sources column
		self.sourcesColumn = QtGui.QVBoxLayout()

		#Add sources list
		self.sourceScrollArea = QtGui.QScrollArea()
		self.sourceScrollArea.setMinimumWidth(340)

		self.sourceFrame = QtGui.QFrame();
		#self.sourceFrame.setFrameStyle(QtGui.QFrame.Box)
		self.sourceFrame.setContentsMargins(0, 0, 0, 0)
		#self.sourceFrame.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

		self.sourceList = QtGui.QVBoxLayout()
		self.sourceList.setContentsMargins(0, 0, 0, 0)
		self.sourceFrame.setLayout(self.sourceList)

		time.sleep(1.)
		
		self.UpdateSourceList()

		self.sourceScrollArea.setWidget(self.sourceFrame)

		self.sourcesColumn.addWidget(self.sourceScrollArea, 1)

		self.selectInputsLayout.addLayout(self.sourcesColumn)
		
		#And right area
		activeSources = []
		for fina in self.inputDeviceToWidgetDict:
			srcWidget = self.inputDeviceToWidgetDict[fina]
			if srcWidget.IsChecked():
				activeSources.append(fina)
		
		self.pano = vidpano.PanoWidget(activeSources)
		self.selectInputsLayout.addWidget(self.pano, 1)
		#self.selectInputsLayout.addWidget(self.view, 1)

		#self.scene = QtGui.QGraphicsScene(self)
		#self.view  = QtGui.QGraphicsView(self.scene)
		
		#self.devNames = self.devManager.list_devices()
		#for fina in self.devNames[:]:
		#	self.devManager.open(fina)
			#self.devManager.set_format(fina, 640, 480, "YUYV");
			#self.devManager.set_format(fina, 800, 600, "MJPEG");
		#	self.devManager.set_format(fina, 640, 480, "MJPEG");
		#	self.devManager.start(fina)
		
		# Create idle timer
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

	def __del__(self):
		print "GuiSources shutting down"
		#self.timer.stop()
		#self.close()
		#del self.devManager

	def UpdateSourceList(self):
		print "UpdateSourceList"
		self.devNames = self.devManager.list_devices()

		for devInfo in self.devNames[:]:

			fina = devInfo[0]
			friendlyName = devInfo[0]
			if len(devInfo) >= 2:
				friendlyName = devInfo[1]
			widget = vidinput.SourceWidget(fina, self.devManager, friendlyName)
			#widget = vidinput.EmulateFixedRateVideoSource(fina, self.devManager, friendlyName)

			QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("source_toggled"), self.VideoSourceToggleEvent)
			self.sourceList.addWidget(widget)
			self.inputDeviceToWidgetDict[fina] = widget

	def ProcessFrame(self, frame, meta, devName):
		
		if 0: #Debug code
			self.frameTestStore.append(frame)
			self.metaTestStore.append(meta)
			while len(self.frameTestStore)>100:
				self.frameTestStore.pop(0)
				self.metaTestStore.pop(0)
			ri = random.randint(0, len(self.frameTestStore)-1)
			randomFrame = self.frameTestStore[ri]
			randomMeta = self.metaTestStore[ri]
			#print len(randomFrame), randomMeta['height']*randomMeta['width']*3, type(randomFrame), randomMeta
			arr = np.array(randomFrame, dtype=np.uint8)
			source = arr.reshape((randomMeta['height'], randomMeta['width'], 3))
			rx = random.randint(0, source.shape[1]-1)
			ry = random.randint(0, source.shape[0]-1)
			#print "random pixel value", source[ry, rx]

		#Estimate frame rates
		if devName not in self.rxTimes:
			self.rxTimes[devName] = []
		timeNow = time.time()
		if len(self.rxTimes[devName]) >= 2 and timeNow - self.rxTimes[devName][0] > 1.:
			print devName, (len(self.rxTimes[devName])-1) / (self.rxTimes[devName][-1] - self.rxTimes[devName][0]), "hz"
			self.rxTimes[devName] = []
		self.rxTimes[devName].append(timeNow)

		#Send frames to processing widgets
		for devId in self.processingWidgets:
			procWidget = self.processingWidgets[devId]
			procWidget.SendFrame(frame, meta, devName)

		#Update GUI with new frame
		#if devName == self.currentSrcId and meta['format'] == "RGB24":
		#	self.scene.clear()
		#	im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		#	pix = QtGui.QPixmap(im2)
		
		#	gpm = QtGui.QGraphicsPixmapItem(pix)
		#	self.scene.addItem(gpm)

		#Send frame to output device
		#for outDevName in self.outputDeviceToWidgetDict:
		#	outWidget = self.outputDeviceToWidgetDict[outDevName]
		#	outWidget.SendFrame(frame, meta, devName)

		#self.pano.SendFrame(frame, meta, devName)

	def IdleEvent(self):
		for fina in self.inputDeviceToWidgetDict:
			camWidget = self.inputDeviceToWidgetDict[fina]
			try:
				camWidget.Update()
			except Exception as err:
				print err

		for fina in self.processingWidgets:
			procWidget = self.processingWidgets[fina]
			try:
				procWidget.Update()
			except Exception as err:
				print err

	def VideoSourceToggleEvent(self, srcId, srcStatus):
		print "VideoSourceToggleEvent", srcId, srcStatus
		if srcStatus:
			self.pano.AddSource(srcId)
		else:
			self.pano.RemoveSource(srcId)