'''
Copyright (c) 2013-2014, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os, random, copy
from PySide import QtGui, QtCore
import guisources
import numpy as np
import videolive

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		
		self.outputDeviceToWidgetDict = {}
		self.processingWidgets = {}
		self.frameTestStore = []
		self.metaTestStore = []
		self.rxTimes = {}

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
		

if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	#QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)

	sys.exit(app.exec_())

