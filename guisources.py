from PySide import QtGui, QtCore
import videolive, vidinput, vidpano, time, vidipcam, viddemocam
import multiprocessing
import traceback, hashlib, uuid, config, sys, StringIO

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
		self.sourceFrame.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
		self.sourceFrame.setFixedWidth(320)

		self.sourceList = QtGui.QVBoxLayout()
		self.sourceList.setContentsMargins(0, 0, 0, 0)
		self.sourceFrame.setLayout(self.sourceList)

		time.sleep(1.)
		
		self.UpdateSourceList()

		self.sourceScrollArea.setWidget(self.sourceFrame)

		self.sourcesColumn.addWidget(self.sourceScrollArea, 1)

		self.addIpCameraButton = QtGui.QPushButton("Add IP Camera")
		self.addIpCameraButton.pressed.connect(self.AddIpCameraPressed)

		self.addDemoCameraButton = QtGui.QPushButton("Add Demo Camera")
		self.addDemoCameraButton.pressed.connect(self.AddDemoCameraPressed)

		self.selectInputsLayout.addLayout(self.sourcesColumn)
		self.sourcesColumn.addWidget(self.addIpCameraButton)
		self.sourcesColumn.addWidget(self.addDemoCameraButton)
		
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
		devWebcamNames = self.devManager.list_devices()

		#Convert to list so items can be updated
		self.devNames = []
		for devInfo in devWebcamNames:
			devInfo = list(devInfo)
			while len(devInfo) < 4: devInfo.append(None)
			if devInfo[2] == None: devInfo[2] = "Local Capture Source"
			self.devNames.append(devInfo)

		#Create camera input widgets
		for devInfo in self.devNames:

			fina = devInfo[0]
			friendlyName = devInfo[0]
			if len(devInfo) >= 2 and devInfo[1] is not None:
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

	def AddIpCameraPressed(self):
		self.camDialog = AddIpCameraDialog(self)
		self.camDialog.exec_()

		if self.camDialog.url is None:
			return

		try:
			self.AddIpCamera(self.camDialog.camType, self.camDialog.url)
		except Exception as err:
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Adding camera failed (is it already present?): " +str(err))
			msgBox.exec_()
	
	def AddIpCamera(self, camType, url, devId = None):

		if devId is None:
			ha = hashlib.sha256()
			prehashStr = str(camType+":"+url.encode('utf-8'))
			print prehashStr
			ha.update(prehashStr)
			devId = ha.hexdigest()
		print "devId", devId

		if devId in self.inputDeviceToWidgetDict:
			raise Exception("Device already added")

		friendlyName = "IP Camera"
		ipCam = vidipcam.IpCamWidget(devId, friendlyName, camType, url)
		self.inputDeviceToWidgetDict[devId] = ipCam

		ipCam.webcamSignal.connect(self.ProcessFrame)
		ipCam.sourceToggled.connect(self.VideoSourceToggleEvent)
		self.sourceList.addWidget(ipCam)
		
		#Resize parent frame
		pix = 0
		for widget in self.inputDeviceToWidgetDict.values():
			pix += widget.sizeHint().height()
		self.sourceFrame.setFixedHeight(pix)

		self.devNames.append([devId, friendlyName, camType, {}])
		self.deviceAdded.emit(devId)

	def AddSourceFromMeta(self, camInfo):
		print "AddSourceFromMeta", camInfo
		if len(camInfo) >= 4 and camInfo[2] == "MJPEG IP Camera":
			try:
				self.AddIpCamera(camInfo[2], camInfo[3]['url'], camInfo[0])
			except Exception as err:
				print err

		if len(camInfo) >= 4 and camInfo[2] == "Local Capture Source":
			pass #This should have been done on init

		if len(camInfo) >= 4 and camInfo[2] == "Demo Camera":
			try:
				self.AddDemoCamera(camInfo[0], camInfo[3]['cam'])
			except Exception as err:
				print err
			
	def AddDemoCamera(self, devId, camFolder = None):

		if devId in self.inputDeviceToWidgetDict:
			raise Exception("Device already added")

		camType = "Demo Camera"
		friendlyName = "Demo Camera"
		ipCam = viddemocam.DemoCamWidget(devId, camFolder)

		ipCam.webcamSignal.connect(self.ProcessFrame)
		ipCam.sourceToggled.connect(self.VideoSourceToggleEvent)
		
		self.sourceList.addWidget(ipCam)
		self.inputDeviceToWidgetDict[devId] = ipCam

		#Resize parent frame
		pixh = 0
		for widget in self.inputDeviceToWidgetDict.values():
			pixh += widget.sizeHint().height()
		self.sourceFrame.setFixedHeight(pixh)

		
		self.devNames.append([devId, friendlyName, camType, {}])
		self.deviceAdded.emit(devId)

	def AddDemoCameraPressed(self):
		devId = str(uuid.uuid4())
		try:
			self.AddDemoCamera(devId)
		except Exception as err:
			print err

#def CalibrateProgressCallback(progress):
#	print "progress", progress

def WorkerProcess(findCorrespondences, cameraArrangement, framePairs, 
	childResultPipe, childProgressPipe,
	childErrorPipe,
	doCorrespondence, doCameraPositions):

	try:
		sys.stdout = StringIO.StringIO()
		sys.stderr = StringIO.StringIO()

		if doCorrespondence:
			#Find point correspondances
			framePairs = findCorrespondences.Calc()

		if framePairs is not None and doCameraPositions:
			#Check there are some points to use for optimisation
			validPairFound = False
			for s in framePairs:
				for pair in s:
					print pair[0], len(pair[3]), len(pair[4])
					if len(pair[3]) > 0 or len(pair[4]) > 0:
						validPairFound = True
			if not validPairFound:
				childErrorPipe.send("No points available for camera estimation")
				return

		if doCameraPositions:
			cameraArrangement.OptimiseCameraPositions(framePairs, childProgressPipe.send)
			cameraArrangement.PrepareForPickle()
			childResultPipe.send((framePairs, cameraArrangement))
		else:
			childResultPipe.send((framePairs, None))

	except Exception as err:
                childErrorPipe.send(str(err) + str(traceback.format_exc()))
		print err
		print traceback.format_exc()
		childResultPipe.send(None)

class CalibratePopup(QtGui.QDialog):

	def __init__(self, parent, findCorrespondences, cameraArrangement):
		QtGui.QDialog.__init__(self, parent)

		self.setWindowTitle('Calibration')
		self.findCorrespondences = findCorrespondences
		self.cameraArrangement = cameraArrangement
		self.done = False
		self.doCorrespondence = True
		self.doCameraPositions = True
		self.framePairs = None
		self.progressPipe = None
		self.errorPipe = None
		self.resultPipe = None
		self.startWorkerThread = False

		#Create gui
		self.layout = QtGui.QVBoxLayout()
		self.setLayout(self.layout)

		self.layout.addWidget(QtGui.QLabel("Calibration progress"))

		self.progressBar = QtGui.QProgressBar()
		self.progressBar.setRange(0., 100.)
		self.progressBar.setValue(0.)
		self.layout.addWidget(self.progressBar)

	def Do(self):

		#Clear old calibration
		self.cameraArrangement.Clear()
		if self.doCorrespondence:
			self.findCorrespondences.Clear()

			#Establish which cameras are used
			self.findCorrespondences.SetActiveCams(self.activeSources)

		if self.doCorrespondence or len(self.findCorrespondences.calibrationFrames) == 0:
			#Store calibration frames
			self.findCorrespondences.StoreCalibration()

		self.startWorkerThread = True

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

	def IdleEvent(self):

		if self.startWorkerThread:

			#Estimate camera directions and parameters
			self.resultPipe, childResultPipe = multiprocessing.Pipe()
			self.progressPipe, childProgressPipe = multiprocessing.Pipe()
			self.errorPipe, childErrorPipe = multiprocessing.Pipe()
			self.findCorrespondences.PrepareForPickle()
			self.cameraArrangement.PrepareForPickle()
			self.process = multiprocessing.Process(target=WorkerProcess, args=(self.findCorrespondences, self.cameraArrangement, 
				self.framePairs, childResultPipe, childProgressPipe, childErrorPipe, self.doCorrespondence, self.doCameraPositions))
			self.process.start()
			#self.cameraArrangement.OptimiseCameraPositions(self.framePairs)

			self.startWorkerThread = False

		if self.progressPipe is not None and self.progressPipe.poll(0.01):
			progress = self.progressPipe.recv()
			print "progress", progress
			self.progressBar.setValue(progress * 100.)

		if self.errorPipe is not None and self.errorPipe.poll(0.01):
			errMsg = self.errorPipe.recv()
			msgBox = QtGui.QMessageBox()
			msgBox.setText(errMsg)
			msgBox.exec_()
			print errMsg
			self.done = True

		if self.resultPipe is not None and self.resultPipe.poll(0.01):
			ret = self.resultPipe.recv()
			print "Data received from worker", type(ret)
			if ret is not None and ret[0] is not None:
				self.framePairs = ret[0]
			if ret is not None and ret[1] is not None:
				self.cameraArrangement = ret[1]
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

		self.urlEdit = QtGui.QLineEdit("type url here") #http://umevakameran.net.umea.se/mjpg/video.mjpg
		self.mainLayout.addWidget(self.urlEdit)

		self.getWebcamUrlsButton = QtGui.QPushButton("Get Example Webcam URLs")
		self.getWebcamUrlsButton.pressed.connect(self.GetWebcamUrlsPressed)
		self.mainLayout.addWidget(self.getWebcamUrlsButton)

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

	def GetWebcamUrlsPressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.EXAMPLE_WEBCAMS_URL))

