'''
Copyright (c) 2013-2014, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os, random, copy
from PySide import QtGui, QtCore
import guisources, guicorrespondences, guipanorama
import numpy as np
import videolive, vidpano, pickle, proj, pano, config

class AboutDialog(QtGui.QDialog):

	def __init__(self, parent = None):
		QtGui.QDialog.__init__(self, parent)

		self.setWindowTitle('About')
		self.setMinimumWidth(500)

		self.mainLayout = QtGui.QVBoxLayout()
		self.setLayout(self.mainLayout)

		self.titleLayout = QtGui.QHBoxLayout()
		self.mainLayout.addLayout(self.titleLayout)

		logo = QtGui.QImage("resources/Kinatomic-Logo-Square-whitebackground300.png")
		logo = logo.scaled(100,100)
		lbl = QtGui.QLabel()
		lbl.setPixmap(QtGui.QPixmap.fromImage(logo))
		lbl.setFixedSize(100, 100)
		self.titleLayout.addWidget(lbl)
		
		self.titleRight = QtGui.QVBoxLayout()
		self.titleLayout.addLayout(self.titleRight)

		title = QtGui.QLabel(config.LONG_PROGRAM_NAME)
		self.titleRight.addWidget(title)

		websiteLink = QtGui.QPushButton("Website")
		self.titleRight.addWidget(websiteLink)
		websiteLink.pressed.connect(self.WebsitePressed)

		legal = QtGui.QTextEdit()
		legal.setText(open("legal.txt", "rt").read())
		legal.setReadOnly(1)
		self.mainLayout.addWidget(legal)

	def WebsitePressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.WEBSITE_URL))

# *********** Main Window *******************

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		self.cameraArrangement = vidpano.CameraArrangement()
		
		self.outputDeviceToWidgetDict = {}
		self.processingWidgets = {}
		self.frameTestStore = []
		self.metaTestStore = []
		self.visObj = None
		self.rxTimes = {}
		self.findCorrespondences = vidpano.FindCorrespondences()

		self.devManager = videolive.Video_in_stream_manager()
		#self.outStreamsManager = videolive.Video_out_stream_manager()
		#self.outFilesManager = videolive.Video_out_file_manager()
	
		self.resize(700, 550)
		self.move(300, 300)
		self.setWindowTitle(config.PROGRAM_NAME)
		self.mainLayout = QtGui.QVBoxLayout()

		#Menu
		self.menubar = self.menuBar()
		fileMenu = self.menubar.addMenu('&File')
		helpMenu = self.menubar.addMenu('&About')

		loadAction = QtGui.QAction('Load', self)
		loadAction.setShortcut('Ctrl+L')
		loadAction.setStatusTip('Load panorama')
		loadAction.triggered.connect(self.LoadButtonPressed)
		fileMenu.addAction(loadAction)

		saveAction = QtGui.QAction('Save', self)
		saveAction.setShortcut('Ctrl+S')
		saveAction.setStatusTip('Save panorama')
		saveAction.triggered.connect(self.SaveButtonPressed)
		fileMenu.addAction(saveAction)

		exitAction = QtGui.QAction('Exit', self)
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.close)
		fileMenu.addAction(exitAction)

		helpAction = QtGui.QAction('Online Help', self)
		helpAction.setStatusTip('Access online help')
		helpAction.triggered.connect(self.HelpPressed)
		helpMenu.addAction(helpAction)

		aboutAction = QtGui.QAction('About', self)
		aboutAction.setStatusTip('Information about the program')
		aboutAction.triggered.connect(self.AboutPressed)
		helpMenu.addAction(aboutAction)

		#Main toolbar
		self.mainToolbarLayout = QtGui.QHBoxLayout()
		self.mainLayout.addLayout(self.mainToolbarLayout)
		self.viewSourcesButton = QtGui.QPushButton("Sources")
		self.viewSourcesButton.pressed.connect(self.ViewSourcesButtonPressed)
		self.viewSourcesButton.setCheckable(True)
		self.viewSourcesButton.setChecked(1)
		self.correspondencesButton = QtGui.QPushButton("Correspondences")
		self.correspondencesButton.pressed.connect(self.ViewCorrespondencesButtonPressed)
		self.correspondencesButton.setCheckable(True)
		self.panoramaButton = QtGui.QPushButton("Panorama")
		self.panoramaButton.pressed.connect(self.ViewPanoramaButtonPressed)
		self.panoramaButton.setCheckable(True)

		self.mainToolbarLayout.addWidget(self.viewSourcesButton)
		self.mainToolbarLayout.addWidget(self.correspondencesButton)
		self.mainToolbarLayout.addWidget(self.panoramaButton)

		self.guiSources = guisources.GuiSources(self.devManager)
		self.guiSources.sourceToggled.connect(self.VideoSourceToggleEvent)
		self.guiSources.webcamSignal.connect(self.ProcessFrame)
		self.guiSources.calibratePressed.connect(self.SourcesCalibratePressed)
		self.guiSources.deviceAdded.connect(self.DeviceAdded)
		self.guiSources.cameraParamsChanged.connect(self.CameraParamsChanged)
		self.cameraArrangement.SetCamParams(self.guiSources.GetCamParams())

		self.guiCorrespondences = guicorrespondences.GuiCorrespondences()
		self.guiCorrespondences.setShown(0)		
		self.guiCorrespondences.optimisePressed.connect(self.CorrespondenceOptimisePressed)

		self.guiPanorama = guipanorama.GuiPanorama()
		self.guiPanorama.setShown(0)
		self.guiPanorama.viewParametersChanged.connect(self.ViewParamsChanged)

		self.mainLayout.addWidget(self.guiSources, 1)
		self.mainLayout.addWidget(self.guiCorrespondences, 1)
		self.mainLayout.addWidget(self.guiPanorama, 1)
		
		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)

		self.show()

		if not config.FULL_VERSION:
			splashDialog = SplashDialog(self, config.FULL_VERSION)
			splashDialog.exec_()

	def __del__(self):
		self.guiSources.Stop()
		print "Shutting down"

	def ViewSourcesButtonPressed(self):
		self.guiSources.setShown(1)
		self.guiCorrespondences.setShown(0)
		self.guiPanorama.setShown(0)

		self.correspondencesButton.setChecked(0)
		self.panoramaButton.setChecked(0)

	def ViewCorrespondencesButtonPressed(self):
		self.guiSources.setShown(0)
		self.guiCorrespondences.setShown(1)
		self.guiPanorama.setShown(0)

		self.viewSourcesButton.setChecked(0)
		self.panoramaButton.setChecked(0)

	def ViewPanoramaButtonPressed(self):
		self.guiSources.setShown(0)
		self.guiCorrespondences.setShown(0)
		self.guiPanorama.setShown(1)

		self.viewSourcesButton.setChecked(0)
		self.correspondencesButton.setChecked(0)

	def VideoSourceToggleEvent(self, srcId, srcStatus):
		pass

	def ProcessFrame(self, frame, meta, devName):
		self.findCorrespondences.ProcessFrame(frame, meta, devName)
		self.guiPanorama.ProcessFrame(frame, meta, devName)
	
	def SourcesCalibratePressed(self, skipOptimiseCams):
		self.Calibration(True, not skipOptimiseCams)

	def CorrespondenceOptimisePressed(self):
		self.Calibration(False, True)

	def Calibration(self, doCorrespondence = True, doCameraPositions = True):

		activeSources = self.guiSources.GetActiveSources()
		
		if len(activeSources) < 2:
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Please select at least two input sources")
			msgBox.exec_()
			return

		if doCorrespondence:
			self.guiPanorama.SetActiveCams(activeSources)
			self.guiCorrespondences.SetActiveCams(activeSources)

		#Estimate correspondences and camera positions
		self.calibratePopup = guisources.CalibratePopup(self, self.findCorrespondences, self.cameraArrangement)
		#self.calibratePopup.setGeometry(QtCore.QRect(100, 100, 400, 200))
		self.calibratePopup.framePairs = self.guiCorrespondences.framePairs
		self.calibratePopup.doCorrespondence = doCorrespondence
		self.calibratePopup.doCameraPositions = doCameraPositions
		self.calibratePopup.activeSources = activeSources
		self.calibratePopup.Do()
		self.calibratePopup.exec_() #Block until done

		self.guiCorrespondences.SetFramePairs(self.calibratePopup.framePairs)
		self.guiCorrespondences.UpdateFrames()
		self.guiCorrespondences.SelectionChanged()

		#Read back results
		if self.calibratePopup.cameraArrangement is not None:
			self.cameraArrangement = self.calibratePopup.cameraArrangement
		if self.calibratePopup.framePairs is not None:
			self.framePairs = self.calibratePopup.cameraArrangement

		if self.cameraArrangement is None and doCameraPositions:
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Camera arrangement not found")
			msgBox.exec_()
			return

		self.UpdatePanoMapping()

		#Update gui with camera parameters
		self.guiSources.SetCamParams(self.cameraArrangement.camParams)

		self.guiCorrespondences.SetFrames(self.findCorrespondences.calibrationFrames, 
			self.findCorrespondences.calibrationMeta)

	def UpdatePanoMapping(self):
		if len(self.cameraArrangement.addedPhotos):
			#Estimate final transform
			outProj = proj.EquirectangularCam()
			outProj.imgW, outProj.imgH = self.guiPanorama.GetOutputSize()
			outProj.cLat, outProj.cLon = self.guiPanorama.GetViewCentre()
			outProj.hFov, outProj.vFov = self.guiPanorama.GetFov()

			if self.visObj is None:
				self.visObj = pano.PanoView(self.cameraArrangement, outProj)
			else:
				self.visObj.SetProjection(outProj)

			self.guiPanorama.SetVisObject(self.visObj, outProj)
		else:
			self.guiPanorama.SetVisObject(None, None)		

	def DeviceAdded(self, devId):
		print "DeviceAdded"

	def ViewParamsChanged(self):
		print "ViewParamsChanged"

		try:
			self.UpdatePanoMapping()		
		except Exception as err:
			print err

	def CameraParamsChanged(self, camParams):
		self.cameraArrangement.SetCamParams(camParams)

	def LoadButtonPressed(self):
		choice = QtGui.QFileDialog.getOpenFileNames(self,
    		caption="Select File to Load Camera Info", filter="Camera config (*.cams)")

		if len(choice[0]) == 0: return
		if len(choice[0][0]) == 0: return

		self.guiCorrespondences.SetFramePairs(None)
		self.cameraArrangement = None
		self.findCorrespondences = None
		inData = pickle.load(open(choice[0][0], "rb"))
		if 'cams' in inData:
			self.cameraArrangement = inData['cams']
		if 'pairs' in inData:
			self.guiCorrespondences.SetFramePairs(inData['pairs'])
		else:
			self.guiCorrespondences.SetFramePairs([])
		if 'correspond' in inData:
			self.findCorrespondences = inData['correspond']

		#self.findCorrespondences.SetActiveCams(self.findCorrespondences.devInputs)
		devInputs = self.findCorrespondences.devInputs
		print "devInputs", devInputs
		self.guiPanorama.SetActiveCams(self.findCorrespondences.devInputs)
		self.guiCorrespondences.SetActiveCams(self.findCorrespondences.devInputs)

		#Create cameras if necessary
		for devInfo in devInputs:
			self.guiSources.AddSourceFromMeta(devInfo)

		#Estimate final transform
		outProj = proj.EquirectangularCam()
		imgW, imgH = self.guiPanorama.GetOutputSize()
		outProj.imgW = imgW
		outProj.imgH = imgH
		self.visObj = pano.PanoView(self.cameraArrangement, outProj)

		self.guiPanorama.SetVisObject(self.visObj, outProj)

		#Update gui with camera parameters
		self.guiSources.SetCamParams(self.cameraArrangement.camParams)

		self.guiCorrespondences.SetFrames(self.findCorrespondences.calibrationFrames, 
			self.findCorrespondences.calibrationMeta)

	def SaveButtonPressed(self):
		choice = QtGui.QFileDialog.getSaveFileName(self,
    		caption="Select File to Save Camera Info", filter="Camera config (*.cams)")

		if len(choice[0]) == 0: return
		self.findCorrespondences.PrepareForPickle()
		self.cameraArrangement.PrepareForPickle()

		#Getting widget settings and update the device list
		for devInfo in self.findCorrespondences.devInputs:
			if devInfo[0] not in self.guiSources.inputDeviceToWidgetDict: continue
			widget = self.guiSources.inputDeviceToWidgetDict[devInfo[0]]
			devInfo[3] = widget.GetSaveParams()

		print self.findCorrespondences.devInputs

		outData = {}
		outData['cams'] = self.cameraArrangement
		outData['pairs'] = self.guiCorrespondences.framePairs
		outData['correspond'] = self.findCorrespondences

		pickle.dump(outData, open(choice[0], "wb"), protocol = -1)

	def HelpPressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.SUPPORT_URL))

	def AboutPressed(self):
		aboutDlg = AboutDialog(self, config.FULL_VERSION)
		aboutDlg.exec_()

def main(console = 0):
	app = QtGui.QApplication(sys.argv)
	mainWindow = MainWindow()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
