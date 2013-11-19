'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os
from PyQt4 import QtGui, QtCore
import videolive
import vidinput, vidoutput, vidstack, vidpano

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		self.inputDeviceToWidgetDict = {}
		self.outputDeviceToWidgetDict = {}
		self.processingWidgets = {}
		self.currentSrcId = None

		self.vidOut = videolive.Video_out_manager()
		self.devManager = videolive.Video_in_manager()
	
		self.resize(700, 550)
		self.move(300, 300)
		self.setWindowTitle('Qt Webcam Demo')

		self.scene = QtGui.QGraphicsScene(self)
		self.view  = QtGui.QGraphicsView(self.scene)

		self.mainLayout = QtGui.QHBoxLayout()

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

		self.UpdateSourceList()

		self.sourceScrollArea.setWidget(self.sourceFrame)

		self.sourcesColumn.addWidget(self.sourceScrollArea, 1)

		#Source add buttons
		self.sourceAddButtons = QtGui.QHBoxLayout()
		self.sourcesColumn.addLayout(self.sourceAddButtons, 0)

		self.addStackButton = QtGui.QPushButton("Add Stack")
		QtCore.QObject.connect(self.addStackButton, QtCore.SIGNAL("clicked()"), self.AddStackPressed)
		self.sourceAddButtons.addWidget(self.addStackButton)

		self.addStackButton = QtGui.QPushButton("Panorama")
		QtCore.QObject.connect(self.addStackButton, QtCore.SIGNAL("clicked()"), self.AddPanoramaPressed)
		self.sourceAddButtons.addWidget(self.addStackButton)

		self.mainLayout.addLayout(self.sourcesColumn)

		#And main view area
		self.mainLayout.addWidget(self.view, 1)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)
		
		#self.vidOut.open("/dev/video4", "YUYV", 640, 480)
		#self.vidOut.open("/dev/video4", "UYVY", 640*2, 480*2)

		time.sleep(1.)

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

		self.show()

	def UpdateSourceList(self):
		print "UpdateSourceList"
		self.devNames = self.devManager.list_devices()

		for devInfo in self.devNames[:]:

                        fina = devInfo[0]
			if self.currentSrcId is None:
				self.currentSrcId = fina
                        friendlyName = devInfo[0]
                        if len(devInfo) >= 2:
                               friendlyName = devInfo[1]

			widget = vidinput.SourceWidget(fina, self.devManager, friendlyName)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("use_source_clicked"), self.ChangeVideoSource)
			self.sourceList.addWidget(widget)
			self.inputDeviceToWidgetDict[fina] = widget

		if 0:
			widget = vidstack.GridStackWidget(self.devNames)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("use_source_clicked"), self.ChangeVideoSource)
			self.sourceList.addWidget(widget)
			self.processingWidgets[widget.devId] = widget

		for fina in self.vidOut.list_devices():
			
			widget = vidoutput.VideoOutWidget(fina, self.vidOut)
			self.sourceList.addWidget(widget)
			self.outputDeviceToWidgetDict[fina] = widget

		self.sourceList.addWidget(widget)

	def ProcessFrame(self, frame, meta, devName):

		#Send frames to processing widgets
		for devId in self.processingWidgets:
			procWidget = self.processingWidgets[devId]
			procWidget.SendFrame(frame, meta, devName)

		#Update GUI with new frame
		if devName == self.currentSrcId and meta['format'] == "RGB24":
			self.scene.clear()
			im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
			pix = QtGui.QPixmap(im2)
		
			gpm = QtGui.QGraphicsPixmapItem(pix)
			self.scene.addItem(gpm)

		#Send frame to output device
		if devName == self.currentSrcId:
			for outDevName in self.outputDeviceToWidgetDict:
				outWidget = self.outputDeviceToWidgetDict[outDevName]
				outWidget.SendFrame(frame, meta, devName)

	def IdleEvent(self):
		for fina in self.inputDeviceToWidgetDict:
			camWidget = self.inputDeviceToWidgetDict[fina]
			camWidget.Update()

		for fina in self.processingWidgets:
			procWidget = self.processingWidgets[fina]
			procWidget.Update()

	def ChangeVideoSource(self, srcId):
		print "ChangeVideoSource", srcId
		self.currentSrcId = srcId

	def AddStackPressed(self):

		#Get list of devices that are selected
		selectedDevs = []
		for devId in self.inputDeviceToWidgetDict:
			dev = self.inputDeviceToWidgetDict[devId]
			if dev.IsChecked():
				selectedDevs.append(devId)

		#Create a processing widget
		widget = vidstack.GridStackWidget(selectedDevs)
		QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
		QtCore.QObject.connect(widget, QtCore.SIGNAL("use_source_clicked"), self.ChangeVideoSource)

		self.sourceFrame.setShown(0)
		self.sourceList.addWidget(widget)
		self.sourceFrame.adjustSize()
		self.sourceFrame.setShown(1)

		self.processingWidgets[widget.devId] = widget

	def AddPanoramaPressed(self):

		#Get list of devices that are selected
		selectedDevs = []
		for devId in self.inputDeviceToWidgetDict:
			dev = self.inputDeviceToWidgetDict[devId]
			if dev.IsChecked():
				selectedDevs.append(devId)

		#Create a processing widget
		widget = vidpano.PanoWidget(selectedDevs)
		QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
		QtCore.QObject.connect(widget, QtCore.SIGNAL("use_source_clicked"), self.ChangeVideoSource)

		self.sourceFrame.setShown(0)
		self.sourceList.addWidget(widget)
		self.sourceFrame.adjustSize()
		self.sourceFrame.setShown(1)

		self.processingWidgets[widget.devId] = widget


if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	#QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)

	sys.exit(app.exec_())

