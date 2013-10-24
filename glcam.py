'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time, os
from PyQt4 import QtGui, QtCore
import v4l2capture

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
		self.currentFrames = {}

		self.resize(700, 550)
		self.move(300, 300)
		self.setWindowTitle('Qt Webcam Demo')

		self.scene = QtGui.QGraphicsScene(self)
		self.view  = QtGui.QGraphicsView(self.scene)

		self.vbox = QtGui.QVBoxLayout()
		self.vbox.addWidget(self.view)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.vbox)
		self.setCentralWidget(centralWidget)
		self.show()

		self.devManager = v4l2capture.Device_manager()
		self.devNames = self.devManager.list_devices()
		for fina in self.devNames[:]:
			self.devManager.open(fina)
			#self.devManager.set_format(fina, 640, 480, "YUYV");
			#self.devManager.set_format(fina, 800, 600, "MJPEG");
			self.devManager.set_format(fina, 640, 480, "MJPEG");
			self.devManager.start(fina)

		self.vidOut = v4l2capture.Video_out_manager()
		self.vidOut.open("/dev/video4", "YUYV", 800, 600)

		# Create idle timer
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

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

