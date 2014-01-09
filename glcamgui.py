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
		self.loadButton = QtGui.QPushButton("Load")
		self.loadButton.pressed.connect(self.LoadButtonPressed)
		self.saveButton = QtGui.QPushButton("Save")
		self.saveButton.pressed.connect(self.SaveButtonPressed)

		self.mainToolbarLayout.addWidget(self.viewSourcesButton)
		self.mainToolbarLayout.addWidget(self.correspondencesButton)
		self.mainToolbarLayout.addWidget(self.panoramaButton)
		self.mainToolbarLayout.addWidget(self.loadButton)
		self.mainToolbarLayout.addWidget(self.saveButton)

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

		self.mainLayout.addWidget(self.guiSources, 1)
		self.mainLayout.addWidget(self.guiCorrespondences, 1)
		self.mainLayout.addWidget(self.guiPanorama, 1)
		
		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)

		self.show()

	def __del__(self):
		self.guiSources.Stop()
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
		pass

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

			#Establish which cameras are used
			activeSources = self.guiSources.GetActiveSources()
			self.findCorrespondences.SetActiveCams(activeSources)
			self.guiPanorama.SetActiveCams(activeSources)
			self.guiCorrespondences.SetActiveCams(activeSources)

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

		self.guiCorrespondences.SetFrames(self.findCorrespondences.calibrationFrames, 
			self.findCorrespondences.calibrationMeta)

	def DeviceAdded(self, devId):
		print "DeviceAdded"

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
		if 'correspond' in inData:
			self.findCorrespondences = inData['correspond']

		#Estimate final transform
		outProj = proj.EquirectangularCam()
		outProj.imgW = 800
		outProj.imgH = 600
		visObj = pano.PanoView(self.cameraArrangement, outProj)

		self.guiPanorama.SetVisObject(visObj)
		self.guiPanorama.SetActiveCams(self.findCorrespondences.devInputs)

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

		outData = {}
		outData['cams'] = self.cameraArrangement
		outData['pairs'] = self.guiCorrespondences.framePairs
		outData['correspond'] = self.findCorrespondences

		pickle.dump(outData, open(choice[0], "wb"), protocol = -1)

def main():
	app = QtGui.QApplication(sys.argv)
	mainWindow = MainWindow()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
