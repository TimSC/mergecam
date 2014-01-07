'''
Copyright (c) 2013-2014, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os, random, copy
from PySide import QtGui, QtCore
import guisources, guicorrespondences, guipanorama
import numpy as np
import videolive, vidpano, pickle, proj, pano

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		self.cameraArrangement = vidpano.CameraArrangement()
		
		self.outputDeviceToWidgetDict = {}
		self.processingWidgets = {}
		self.frameTestStore = []
		self.metaTestStore = []
		self.rxTimes = {}
		self.findCorrespondences = vidpano.FindCorrespondences()

		self.devManager = videolive.Video_in_stream_manager()
		#self.outStreamsManager = videolive.Video_out_stream_manager()
		#self.outFilesManager = videolive.Video_out_file_manager()
	
		self.resize(700, 550)
		self.move(300, 300)
		self.setWindowTitle('Kinatomic PanoramaVid')
		self.mainLayout = QtGui.QVBoxLayout()

		#Main toolbar
		self.mainToolbarLayout = QtGui.QHBoxLayout()
		self.mainLayout.addLayout(self.mainToolbarLayout)
		self.viewSourcesButton = QtGui.QPushButton("Sources")
		self.viewSourcesButton.pressed.connect(self.ViewSourcesButtonPressed)
		self.correspondencesButton = QtGui.QPushButton("Correspondences")
		self.correspondencesButton.pressed.connect(self.ViewCorrespondencesButtonPressed)
		self.panoramaButton = QtGui.QPushButton("Panorama")
		self.panoramaButton.pressed.connect(self.ViewPanoramaButtonPressed)
		self.mainToolbarLayout.addWidget(self.viewSourcesButton)
		self.mainToolbarLayout.addWidget(self.correspondencesButton)
		self.mainToolbarLayout.addWidget(self.panoramaButton)

		self.guiSources = guisources.GuiSources(self.devManager)
		self.guiSources.sourceToggled.connect(self.VideoSourceToggleEvent)
		self.guiSources.webcamSignal.connect(self.ProcessFrame)
		self.guiSources.calibratePressed.connect(self.SourcesCalibratePressed)
		self.guiSources.deviceListChanged.connect(self.DeviceListChanged)
		self.guiSources.cameraParamsChanged.connect(self.CameraParamsChanged)
		self.cameraArrangement.SetCamParams(self.guiSources.GetCamParams())

		activeSources = self.guiSources.GetActiveSources()
		for srcId in activeSources:
			self.findCorrespondences.AddSource(srcId)

		self.guiCorrespondences = guicorrespondences.GuiCorrespondences(self.findCorrespondences)
		self.guiCorrespondences.setShown(0)
		self.guiCorrespondences.SetDeviceList(self.guiSources.devNames)
		self.guiCorrespondences.optimisePressed.connect(self.CorrespondenceOptimisePressed)

		self.guiPanorama = guipanorama.GuiPanorama(self.findCorrespondences, self.cameraArrangement)
		self.guiPanorama.setShown(0)

		self.mainLayout.addWidget(self.guiSources, 1)
		self.mainLayout.addWidget(self.guiCorrespondences, 1)
		self.mainLayout.addWidget(self.guiPanorama, 1)
		
		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)

		self.show()

	def __del__(self):
		print "Shutting down"

	def ViewSourcesButtonPressed(self):
		self.guiSources.setShown(1)
		self.guiCorrespondences.setShown(0)
		self.guiPanorama.setShown(0)

	def ViewCorrespondencesButtonPressed(self):
		self.guiSources.setShown(0)
		self.guiCorrespondences.setShown(1)
		self.guiPanorama.setShown(0)

	def ViewPanoramaButtonPressed(self):
		self.guiSources.setShown(0)
		self.guiCorrespondences.setShown(0)
		self.guiPanorama.setShown(1)

	def VideoSourceToggleEvent(self, srcId, srcStatus):
		print "VideoSourceToggleEvent", srcId, srcStatus
		if srcStatus == 1:
			self.findCorrespondences.AddSource(srcId)
		else:
			self.findCorrespondences.RemoveSource(srcId)
		self.guiCorrespondences.UpdateActiveDevices()

	def ProcessFrame(self, frame, meta, devName):
		self.findCorrespondences.ProcessFrame(frame, meta, devName)
		self.guiPanorama.ProcessFrame(frame, meta, devName)
	
	def SourcesCalibratePressed(self, skipOptimiseCams):
		self.Calibration(True, not skipOptimiseCams)

	def CorrespondenceOptimisePressed(self):
		self.Calibration(False, True)

	def Calibration(self, doCorrespondence = True, doCameraPositions = True):
		#Clear old calibration
		self.cameraArrangement.Clear()
		if doCorrespondence:
			self.findCorrespondences.Clear()

		#Estimate correspondences and camera positions
		self.calibratePopup = guisources.CalibratePopup(self, self.findCorrespondences, self.cameraArrangement)
		self.calibratePopup.setGeometry(QtCore.QRect(100, 100, 400, 200))
		self.calibratePopup.framePairs = self.guiCorrespondences.framePairs
		self.calibratePopup.doCorrespondence = doCorrespondence
		self.calibratePopup.doCameraPositions = doCameraPositions
		self.calibratePopup.Do()
		self.calibratePopup.exec_() #Block until done
		self.guiCorrespondences.SetFramePairs(self.calibratePopup.framePairs)
		self.guiCorrespondences.UpdateFrames()
		self.guiCorrespondences.SelectionChanged()

		#Read back results
		self.cameraArrangement = self.calibratePopup.cameraArrangement
		if self.cameraArrangement is None:
			raise Exception("Camera arrangement not found")

		#Estimate final transform
		outProj = proj.EquirectangularCam()
		outProj.imgW = 800
		outProj.imgH = 600
		visObj = pano.PanoView(self.cameraArrangement, outProj)

		self.guiPanorama.SetVisObject(visObj)

		#Update gui with camera parameters
		self.guiSources.SetCamParams(self.cameraArrangement.camParams)

	def DeviceListChanged(self, deviceList):
		print "DeviceListChanged"
		self.findCorrespondences.SetDeviceList(deviceList)

	def CameraParamsChanged(self, camParams):
		self.cameraArrangement.SetCamParams(camParams)

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	mainWindow = MainWindow()
	sys.exit(app.exec_())

