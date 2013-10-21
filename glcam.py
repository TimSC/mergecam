'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time
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
		self.devManager.open()
		self.devManager.set_format("/dev/video0", 640, 480, "MJPEG");
		self.devManager.start()
		


		# Create idle timer
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

	def ProcessFrame(self, im):
		print "Frame update", len(im)
		#camId = im[4]
		camId = 0
		if camId in self.currentFrames:
			self.scene.removeItem(self.currentFrames[camId])
			del self.currentFrames[camId]

		#self.scene.clear()

		im2 = QtGui.QImage(im, 640, 480, QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap(im2)
		
		#Calc an index for camera
		gpm = QtGui.QGraphicsPixmapItem(pix)
		self.currentFrames[camId] = gpm
		camKeys = self.currentFrames.keys()
		camKeys.sort()
		ind = camKeys.index(camId)
		x = ind / 2
		y = ind % 2
		gpm.setPos(x * 640, y * 480)
		
		self.scene.addItem(gpm)

	def IdleEvent(self):
		fr = self.devManager.get_frame()
		if fr is not None:
			print len(fr)
			self.ProcessFrame(fr)

if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	#QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)

	sys.exit(app.exec_())

