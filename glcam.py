'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os
from PyQt4 import QtGui, QtCore
import v4l2capture

class SourceWidget(QtGui.QFrame):
	def __init__(self, srcId):
		QtGui.QFrame.__init__(self)

		self.widgetLayout = QtGui.QVBoxLayout(self)

		self.srcId = srcId

		label = QtGui.QLabel(srcId)
		self.widgetLayout.addWidget(label, 0)

		img = QtGui.QImage(300, 200, QtGui.QImage.Format_RGB888)
		self.pic = QtGui.QLabel()
		self.pic.setGeometry(10, 10, 300, 200)
		self.pic.setMinimumSize(300, 200)
		self.pic.setPixmap(QtGui.QPixmap.fromImage(img))
		self.widgetLayout.addWidget(self.pic, 0)

		self.setMaximumSize(300,300)
		self.setFrameStyle(QtGui.QFrame.Box)

	def UpdateFrame(self, frame, meta):
		if meta['format'] != "RGB24": return

		img = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		imgs = img.scaled(300, 200)
		px = QtGui.QPixmap.fromImage(imgs)
		self.pic.setPixmap(px)

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}
		self.deviceToWidgetDict = {}

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

			frame = QtGui.QFrame();

			s.setMinimumWidth(320)
			self.sourceList = QtGui.QVBoxLayout()

			frame.setLayout(self.sourceList)
			frame.setMinimumWidth(300)
			frame.setMinimumHeight(600)
			frame.setMaximumHeight(4000)
			frame.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

			s.setWidget(frame)
			s.setMinimumHeight(600)
			s.setMaximumHeight(4000)
			s.setMinimumWidth(300)

			self.mainLayout.addWidget(s)


		#And main view area
		self.mainLayout.addWidget(self.view, 1)

		

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)
		

		self.vidOut = v4l2capture.Video_out_manager()
		#self.vidOut.open("/dev/video4", "YUYV", 640, 480)
		#self.vidOut.open("/dev/video4", "UYVY", 640*2, 480*2)

		time.sleep(1.)

		self.devManager = v4l2capture.Device_manager()
		self.devNames = self.devManager.list_devices()
		for fina in self.devNames[:]:
			self.devManager.open(fina)
			#self.devManager.set_format(fina, 640, 480, "YUYV");
			#self.devManager.set_format(fina, 800, 600, "MJPEG");
			self.devManager.set_format(fina, 640, 480, "MJPEG");
			self.devManager.start(fina)

		self.UpdateSourceList()

		# Create idle timer
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

		self.show()

	def UpdateSourceList(self):
		
		self.devNames = self.devManager.list_devices()
		for fina in self.devNames[:]:
			widget = SourceWidget(fina)
			widget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
			self.sourceList.addWidget(widget, 0)
			self.deviceToWidgetDict[fina] = widget

	def ProcessFrame(self, frame, meta, devName):

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

		if devName in self.deviceToWidgetDict:
			self.deviceToWidgetDict[devName].UpdateFrame(frame, meta)
		

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
		for fina in self.devNames[:]:
			data = self.devManager.get_frame(fina)
			if data is not None:
				print len(data[0])
				self.ProcessFrame(data[0], data[1], fina)

if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	#QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)

	sys.exit(app.exec_())

