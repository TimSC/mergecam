'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os
from PyQt4 import QtGui, QtCore
import v4l2capture

class SourceWidget(QtGui.QFrame):
	def __init__(self, srcId, devManager):
		QtGui.QFrame.__init__(self)

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		self.srcId = srcId
		self.cameraOn = False
		self.devManager = devManager

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		label = QtGui.QLabel(srcId)
		self.toolbar.addWidget(label, 0)

		self.onButton = QtGui.QPushButton("On")
		self.toolbar.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		self.useButton = QtGui.QPushButton("Use")
		self.toolbar.addWidget(self.useButton, 0)
		QtCore.QObject.connect(self.useButton, QtCore.SIGNAL('clicked()'), self.ClickedUse)

		#Create video preview
		img = QtGui.QImage(300, 200, QtGui.QImage.Format_RGB888)
		self.pic = QtGui.QLabel()
		self.pic.setPixmap(QtGui.QPixmap.fromImage(img))
		self.widgetLayout.addWidget(self.pic, 0)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

		#Start video
		self.ClickedOn()
	
	def Update(self):

		if self.cameraOn:
			data = self.devManager.get_frame(self.srcId)

			if data is not None:
				#print len(data[0])
				self.emit(QtCore.SIGNAL('webcam_frame'), data[0], data[1], self.srcId)
				self.UpdatePreview(data[0], data[1])

	def UpdatePreview(self, frame, meta):
		if meta['format'] != "RGB24": return

		img = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		imgs = img.scaled(300, 200)
		px = QtGui.QPixmap.fromImage(imgs)
		self.pic.setPixmap(px)

	def ClearPreview(self):
		img = QtGui.QImage(300, 200, QtGui.QImage.Format_RGB888)
		img.fill(QtGui.QColor(0, 0, 0))
		px = QtGui.QPixmap.fromImage(img)
		self.pic.setPixmap(px)
		
	def ClickedOn(self):

		if self.cameraOn:
			self.cameraOn = False
			self.devManager.stop(self.srcId)
			self.devManager.close(self.srcId)
			self.ClearPreview()
			self.onButton.setChecked(0)
		else:
			self.cameraOn = True
			self.devManager.open(self.srcId)
			self.devManager.set_format(self.srcId, 640, 480, "MJPEG")
			self.devManager.start(self.srcId)
		
		self.onButton.setChecked(self.cameraOn)

	def ClickedUse(self):
		if not self.cameraOn:
			self.ClickedOn()

		self.emit(QtCore.SIGNAL('use_source_clicked'), self.srcId)

class VideoOutWidget(QtGui.QFrame):
	def __init__(self, devId, videoOutManager):
		QtGui.QFrame.__init__(self)
		self.devId = devId
		self.devOn = False
		self.videoOutManager = videoOutManager

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		label = QtGui.QLabel(devId)
		self.toolbar.addWidget(label, 0)

		self.onButton = QtGui.QPushButton("On")
		self.toolbar.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

		self.standbyGraphic = None

	def ClickedOn(self):

		if self.devOn:
			self.devOn = False
			self.videoOutManager.close(self.devId)
		else:
			self.devOn = True
			self.videoOutManager.open(self.devId, "YUYV", 640, 480)

			if self.standbyGraphic is None:
				img = QtGui.QImage("standby_graphic.jpg")
				img2 = QtGui.QPixmap.fromImage(img)
				img3 = img2.scaled(640, 480)
				img4 = img3.toImage()
				self.standbyGraphic = img4.convertToFormat(QtGui.QImage.Format_RGB888)
			
			if self.standbyGraphic is not None:
				raw = self.standbyGraphic.bits().asstring(self.standbyGraphic.numBytes())
				self.videoOutManager.send_frame(self.devId, str(raw), "RGB24", 
					self.standbyGraphic.width(), self.standbyGraphic.height())

		self.onButton.setChecked(self.devOn)


class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		self.deviceToWidgetDict = {}
		self.currentSrcId = None

		self.vidOut = v4l2capture.Video_out_manager()
		self.devManager = v4l2capture.Device_manager()

		self.resize(700, 550)
		self.move(300, 300)
		self.setWindowTitle('Qt Webcam Demo')

		self.scene = QtGui.QGraphicsScene(self)
		self.view  = QtGui.QGraphicsView(self.scene)

		self.mainLayout = QtGui.QHBoxLayout()

		#Add sources list
		if 0:
			s = QtGui.QScrollArea()
			#s.setMinimumWidth(320)
			w = QtGui.QWidget(s)
			self.sourceList = QtGui.QVBoxLayout(w)
			self.mainLayout.addWidget(s)

		if 1:
			s = QtGui.QScrollArea()
			s.setMinimumWidth(340)

			frame = QtGui.QFrame();
			#frame.setFrameStyle(QtGui.QFrame.Box)
			frame.setContentsMargins(0, 0, 0, 0)

			self.sourceList = QtGui.QVBoxLayout()
			self.sourceList.setContentsMargins(0, 0, 0, 0)
			frame.setLayout(self.sourceList)


			self.UpdateSourceList()

			s.setWidget(frame)
			self.mainLayout.addWidget(s)


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
		
		self.devNames = self.devManager.list_devices()
		for fina in self.devNames[:]:

			if self.currentSrcId is None:
				self.currentSrcId = fina

			widget = SourceWidget(fina, self.devManager)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
			QtCore.QObject.connect(widget, QtCore.SIGNAL("use_source_clicked"), self.ChangeVideoSource)
			self.sourceList.addWidget(widget)
			self.deviceToWidgetDict[fina] = widget

		for fina in self.vidOut.list_devices():
			
			widget = VideoOutWidget(fina, self.vidOut)
			self.sourceList.addWidget(widget)

	def ProcessFrame(self, frame, meta, devName):

		if devName == self.currentSrcId:
			self.scene.clear()
			im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
			pix = QtGui.QPixmap(im2)
		
			#Calc an index for camera
			gpm = QtGui.QGraphicsPixmapItem(pix)
			self.scene.addItem(gpm)

	def OldFunc(self):
		try:
			if devName == "/dev/video0":
				image = QtGui.QImage(800, 600, QtGui.QImage.Format_RGB888)
				painter = QtGui.QPainter(image)
				painter.setRenderHint(QtGui.QPainter.Antialiasing)
				self.scene.render(painter)
				del painter
				raw = image.bits().asstring(image.numBytes())
				
				self.vidOut.send_frame("/dev/video4", str(raw), "RGB24", 800, 600)

		except Exception as err:
			print err

		#if devName in self.deviceToWidgetDict:
		#	self.deviceToWidgetDict[devName].UpdateFrame(frame, meta)
		

		camId = devName
		if camId in self.currentFrames:
			self.scene.removeItem(self.currentFrames[camId])
			del self.currentFrames[camId]

		#self.scene.clear()
		if meta['format'] != "RGB24": 
			print "Cannot display format", meta['format']
			return

		im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap(im2)
		
		#Calc an index for camera
		gpm = QtGui.QGraphicsPixmapItem(pix)
		self.currentFrames[camId] = gpm
		camKeys = self.currentFrames.keys()
		camKeys.sort()
		ind = camKeys.index(camId)
		x = ind / 2
		y = ind % 2
		gpm.setPos(x * meta['width'], y * meta['height'])
		
		self.scene.addItem(gpm)

	def IdleEvent(self):
		for fina in self.deviceToWidgetDict:
			camWidget = self.deviceToWidgetDict[fina]
			camWidget.Update()

	def ChangeVideoSource(self, srcId):
		print "ChangeVideoSource", srcId
		self.currentSrcId = srcId

if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	#QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)

	sys.exit(app.exec_())

