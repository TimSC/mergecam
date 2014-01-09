from PySide import QtGui, QtCore
import videolive, vidinput, vidpano, time, vidipcam
import multiprocessing
import traceback, uuid

class GuiSources(QtGui.QFrame):
	sourceToggled = QtCore.Signal(str, int)
	webcamSignal = QtCore.Signal(bytearray, dict, str)
	calibratePressed = QtCore.Signal(int)
	deviceAdded = QtCore.Signal(list)
	deviceRemoved = QtCore.Signal(list)
	cameraParamsChanged = QtCore.Signal(dict)

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

		self.addIpCameraButton = QtGui.QPushButton("Add IP Camera")
		self.addIpCameraButton.pressed.connect(self.AddIpCamera)

		self.selectInputsLayout.addLayout(self.sourcesColumn)
		self.sourcesColumn.addWidget(self.addIpCameraButton)
		
		self.pano = vidpano.LensParamsWidget()
		self.pano.calibratePressed.connect(self.ClickedCalibrate)
		self.pano.cameraParamsChanged.connect(self.CameraParamsChanged)
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
		for dev in self.inputDeviceToWidgetDict.values():
			dev.Stop()
		#self.timer.stop()
		#self.close()
		#del self.devManager

	def Stop(self):
		for dev in self.inputDeviceToWidgetDict.values():
			dev.Stop()

	def GetActiveSources(self):
		activeSources = []
		for li in self.devNames:
			srcWidget = self.inputDeviceToWidgetDict[li[0]]
			if srcWidget.IsChecked():
				activeSources.append(li)
		return activeSources

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

			widget.webcamSignal.connect(self.ProcessFrame)
			widget.sourceToggled.connect(self.VideoSourceToggleEvent)
			self.sourceList.addWidget(widget)
			self.inputDeviceToWidgetDict[fina] = widget

			self.deviceAdded.emit(fina)
		
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
			if 0:
				print devName, (len(self.rxTimes[devName])-1) / (self.rxTimes[devName][-1] - self.rxTimes[devName][0]), "hz"
			self.rxTimes[devName] = []
		self.rxTimes[devName].append(timeNow)

		self.webcamSignal.emit(frame, meta, devName)

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
		self.sourceToggled.emit(srcId, srcStatus)

	def ClickedCalibrate(self, skipOptimiseCams):
		self.calibratePressed.emit(skipOptimiseCams)

	def CameraParamsChanged(self, camParams):
		self.cameraParamsChanged.emit(camParams)
		
	def GetCamParams(self):
		return self.pano.GetCamParams()
	
	def SetCamParams(self, params):
		self.pano.SetCamParams(params)

	def AddIpCamera(self):
		self.camDialog = AddIpCameraDialog(self)
		self.camDialog.exec_()

		if self.camDialog.url is None:
			return
		
		camNamespace = uuid.UUID('c58012b7-7020-4418-a389-f79b6f075978')
		devId = uuid.uuid5(camNamespace, str(self.camDialog.url))
		print "devId", devId

		if devId in self.inputDeviceToWidgetDict:
			raise Exception("Device already added")

		friendlyName = "IP Camera"
		ipCam = vidipcam.IpCamWidget(devId, friendlyName, self.camDialog.camType, self.camDialog.url)

		ipCam.webcamSignal.connect(self.ProcessFrame)
		ipCam.sourceToggled.connect(self.VideoSourceToggleEvent)
		self.sourceList.addWidget(ipCam)
		self.inputDeviceToWidgetDict[devId] = ipCam
		self.devNames.append((devId, friendlyName, self.camDialog.camType, self.camDialog.url))

		self.deviceAdded.emit(devId)

#def CalibrateProgressCallback(progress):
#	print "progress", progress

def WorkerProcess(cameraArrangement, framePairs, childResultPipe, childProgressPipe):
	try:
		cameraArrangement.OptimiseCameraPositions(framePairs, childProgressPipe.send)
		cameraArrangement.PrepareForPickle()
		childResultPipe.send(cameraArrangement)
	except Exception as err:
		print err
		print traceback.format_exc()
		childResultPipe.send(None)

class CalibratePopup(QtGui.QDialog):

	def __init__(self, parent, findCorrespondences, cameraArrangement):
		QtGui.QDialog.__init__(self, parent)

		self.findCorrespondences = findCorrespondences
		self.cameraArrangement = cameraArrangement
		self.done = False
		self.doCorrespondence = True
		self.doCameraPositions = True
		self.framePairs = None
		self.progressPipe = None
		self.resultPipe = None

	def Do(self):

		#Create gui
		self.layout = QtGui.QVBoxLayout()
		self.setLayout(self.layout)

		self.layout.addWidget(QtGui.QLabel("Calibration progress"))

		self.progressBar = QtGui.QProgressBar()
		self.progressBar.setRange(0., 100.)
		self.progressBar.setValue(0.)
		self.layout.addWidget(self.progressBar)

		if self.doCorrespondence or len(self.findCorrespondences.calibrationFrames) == 0:
			#Store calibration frames
			self.findCorrespondences.StoreCalibration()

		if self.doCorrespondence:
			#Find point correspondances
			self.framePairs = self.findCorrespondences.Calc()

		if self.doCameraPositions:

			#Check there are some points to use for optimisation
			validPairFound = False
			for s in self.framePairs:
				for pair in s:
					if len(pair[3]) > 0 or len(pair[4]) > 0:
						validPairFound = True
			if not validPairFound:
				raise Exception("No points available for camera estimation")

			#Estimate camera directions and parameters
			self.resultPipe, childResultPipe = multiprocessing.Pipe()
			self.progressPipe, childProgressPipe = multiprocessing.Pipe()
			self.process = multiprocessing.Process(target=WorkerProcess, args=(self.cameraArrangement, 
				self.framePairs, childResultPipe, childProgressPipe))
			self.process.start()
			#self.cameraArrangement.OptimiseCameraPositions(self.framePairs)
		else:
			self.done = True

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

	def IdleEvent(self):
		if self.progressPipe is not None and self.progressPipe.poll(0.01):
			progress = self.progressPipe.recv()
			print "progress", progress
			self.progressBar.setValue(progress * 100.)

		if self.resultPipe is not None and self.resultPipe.poll(0.01):
			self.cameraArrangement = self.resultPipe.recv()
			print "Data received from worker", self.cameraArrangement
			if self.cameraArrangement is not None:
				print self.cameraArrangement.addedPhotos

			self.done = True

		if self.done:
			self.close()

	def closeEvent(self, event):
		if not self.done:
			event.ignore()


class AddIpCameraDialog(QtGui.QDialog):

	def __init__(self, parent):
		QtGui.QDialog.__init__(self, parent)

		self.url = None
		self.camType = None

		self.mainLayout = QtGui.QVBoxLayout()
		self.setLayout(self.mainLayout)

		self.camTypeCombo = QtGui.QComboBox()
		self.camTypeCombo.addItem("MJPEG IP Camera")
		self.mainLayout.addWidget(self.camTypeCombo)

		self.urlEdit = QtGui.QLineEdit("http://umevakameran.net.umea.se/mjpg/video.mjpg")#("url")
		self.mainLayout.addWidget(self.urlEdit)

		self.buttonLayout = QtGui.QHBoxLayout()
		self.mainLayout.addLayout(self.buttonLayout)

		self.okButton = QtGui.QPushButton("OK")
		self.buttonLayout.addWidget(self.okButton)
		self.okButton.pressed.connect(self.OkPressed)

		self.cancelButton = QtGui.QPushButton("Cancel")
		self.buttonLayout.addWidget(self.cancelButton)
		self.cancelButton.pressed.connect(self.CancelPressed)

	def OkPressed(self):
		self.url = self.urlEdit.text()
		self.camType = self.camTypeCombo.currentText()
		self.close()

	def CancelPressed(self):
		self.close()


