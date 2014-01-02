'''
Copyright (c) 2013-2014, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os, random, copy
from PySide import QtGui, QtCore
import guisources
import numpy as np
import videolive, vidpano

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
		QtCore.QObject.connect(self.viewSourcesButton, QtCore.SIGNAL("pressed()"), self.ViewSourcesButtonPressed)
		self.correspondencesButton = QtGui.QPushButton("Correspondences")
		QtCore.QObject.connect(self.correspondencesButton, QtCore.SIGNAL("pressed()"), self.ViewCorrespondencesButtonPressed)
		self.panoramaButton = QtGui.QPushButton("Panorama")
		QtCore.QObject.connect(self.panoramaButton, QtCore.SIGNAL("pressed()"), self.ViewPanoramaButtonPressed)
		self.mainToolbarLayout.addWidget(self.viewSourcesButton)
		self.mainToolbarLayout.addWidget(self.correspondencesButton)
		self.mainToolbarLayout.addWidget(self.panoramaButton)

		self.guiSources = guisources.GuiSources(self.devManager)
		self.guiSources.sourceToggled.connect(self.VideoSourceToggleEvent)
		self.guiSources.webcamSignal.connect(self.ProcessFrame)
		self.guiSources.calibratePressed.connect(self.CalibratePressed)

		activeSources = self.guiSources.GetActiveSources()
		for srcId in activeSources:
			self.findCorrespondences.AddSource(srcId)

		self.mainLayout.addWidget(self.guiSources, 1)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)

		self.show()

	def __del__(self):
		print "Shutting down"

	def ViewSourcesButtonPressed(self):
		self.guiSources.setShown(1)

	def ViewCorrespondencesButtonPressed(self):
		self.guiSources.setShown(0)

	def ViewPanoramaButtonPressed(self):
		self.guiSources.setShown(0)

	def VideoSourceToggleEvent(self, srcId, srcStatus):
		print "VideoSourceToggleEvent", srcId, srcStatus
		if srcStatus == 1:
			self.findCorrespondences.AddSource(srcId)
		else:
			self.findCorrespondences.RemoveSource(srcId)

	def ProcessFrame(self, frame, meta, devName):
		self.findCorrespondences.ProcessFrame(frame, meta, devName)
	
	def CalibratePressed(self):
		self.findCorrespondences.StoreCalibration()
		self.findCorrespondences.Calc()

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	mainWindow = MainWindow()
	sys.exit(app.exec_())

