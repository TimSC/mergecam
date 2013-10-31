'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os, uuid
from PyQt4 import QtGui, QtCore
import v4l2capture

class SourceWidget(QtGui.QFrame):
	def __init__(self, devId, devManager):
		QtGui.QFrame.__init__(self)

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		self.devId = devId
		self.cameraOn = False
		self.devManager = devManager

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.toolbar.addWidget(self.checkbox, 0)

		label = QtGui.QLabel(devId)
		self.toolbar.addWidget(label, 1)

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
			data = self.devManager.get_frame(self.devId)

			if data is not None:
				#print len(data[0])
				self.emit(QtCore.SIGNAL('webcam_frame'), data[0], data[1], self.devId)
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
			self.devManager.stop(self.devId)
			self.devManager.close(self.devId)
			self.ClearPreview()
		else:
			self.cameraOn = True
			self.devManager.open(self.devId)
			self.devManager.set_format(self.devId, 640, 480, "MJPEG")
			self.devManager.start(self.devId)
		
		self.onButton.setChecked(self.cameraOn)

	def ClickedUse(self):
		if not self.cameraOn:
			self.ClickedOn()

		self.emit(QtCore.SIGNAL('use_source_clicked'), self.devId)

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

		self.checkbox = QtGui.QCheckBox()
		self.toolbar.addWidget(self.checkbox, 0)

		label = QtGui.QLabel(devId)
		self.toolbar.addWidget(label, 1)

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

	def SendFrame(self, frame, meta, devName):
		if not self.devOn: return
		if meta['format'] != "RGB24": return

		im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap(im2)
		pixmap2 = pix.scaled(640, 480)
		img = pixmap2.toImage()
		img2 = img.convertToFormat(QtGui.QImage.Format_RGB888)
		raw = img2.bits().asstring(img2.numBytes())
		self.videoOutManager.send_frame(self.devId, str(raw), "RGB24", 
			img2.width(), img2.height())

	def Update(self):

		if self.cameraOn:
			if 0:
				#print len(data[0])
				self.emit(QtCore.SIGNAL('webcam_frame'), data[0], data[1], self.devId)
				self.UpdatePreview(data[0], data[1])


class GridStackWidget(QtGui.QFrame):
	def __init__(self, devInputs):
		QtGui.QFrame.__init__(self)
		self.devOn = False
		self.devId = uuid.uuid4()
		self.devInputs = devInputs
		self.canvas = QtGui.QImage(640*2, 480*2, QtGui.QImage.Format_RGB888)
		self.framesRcvSinceOutput = set()
		self.outBuffer = []

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.toolbar.addWidget(self.checkbox, 0)

		label = QtGui.QLabel("Stack Videos")
		self.toolbar.addWidget(label, 1)

		self.onButton = QtGui.QPushButton("On")
		self.toolbar.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		self.useButton = QtGui.QPushButton("Use")
		self.toolbar.addWidget(self.useButton, 0)
		QtCore.QObject.connect(self.useButton, QtCore.SIGNAL('clicked()'), self.ClickedUse)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

	def ClickedOn(self):

		if self.devOn:
			self.devOn = False
		else:
			self.devOn = True
		print self.devOn
		self.onButton.setChecked(self.devOn)

	def SendFrame(self, frame, meta, devName):
		if not self.devOn: return
		if devName not in self.devInputs: return

		devIndex = self.devInputs.index(devName)
		x = devIndex / 2
		y = devIndex % 2

		img = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		
		painter = QtGui.QPainter(self.canvas)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		painter.drawImage(640 * x, 480 * y, img)
		del painter

		if devName in self.framesRcvSinceOutput:
			#We have received this frame again; it is time to write output
			raw = self.canvas.bits().asstring(self.canvas.numBytes())
			metaOut = {'width': self.canvas.width(), 'height': self.canvas.height(), 'format': 'RGB24'}
			self.outBuffer.append([raw, metaOut])
			self.framesRcvSinceOutput = set()

		self.framesRcvSinceOutput.add(devName)

	def Update(self):
		for result in self.outBuffer:
			self.emit(QtCore.SIGNAL('webcam_frame'), result[0], result[1], self.devId)
		self.outBuffer = []

	def ClickedUse(self):
		if not self.devOn:
			self.ClickedOn()

		self.emit(QtCore.SIGNAL('use_source_clicked'), self.devId)

		
class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		self.inputDeviceToWidgetDict = {}
		self.outputDeviceToWidgetDict = {}
		self.processingWidgets = {}
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
			self.inputDeviceToWidgetDict[fina] = widget

		widget = GridStackWidget(self.devNames)
		QtCore.QObject.connect(widget, QtCore.SIGNAL("webcam_frame"), self.ProcessFrame)
		QtCore.QObject.connect(widget, QtCore.SIGNAL("use_source_clicked"), self.ChangeVideoSource)
		self.sourceList.addWidget(widget)
		self.processingWidgets[widget.devId] = widget

		for fina in self.vidOut.list_devices():
			
			widget = VideoOutWidget(fina, self.vidOut)
			self.sourceList.addWidget(widget)
			self.outputDeviceToWidgetDict[fina] = widget

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
		for fina in self.inputDeviceToWidgetDict:
			camWidget = self.inputDeviceToWidgetDict[fina]
			camWidget.Update()

		for fina in self.processingWidgets:
			procWidget = self.processingWidgets[fina]
			procWidget.Update()

	def ChangeVideoSource(self, srcId):
		print "ChangeVideoSource", srcId
		self.currentSrcId = srcId

if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	#QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)

	sys.exit(app.exec_())

