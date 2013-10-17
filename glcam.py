'''
Copyright (c) 2013, Tim Sheerman-Chase
All rights reserved.
'''
import sys, time
from PyQt4 import QtGui, QtCore
from media import v4l2cap

class CamWorker(QtCore.QThread): 
    def __init__(self): 
		super(CamWorker, self).__init__() 
		self.devList = v4l2cap.ListDevices()
		print self.devList
		self.devs = []

    def run(self):
		for devName in self.devList[1:2]:
			v4l2 = v4l2cap.V4L2()
			v4l2.Start(devName[0])
			print "Started", devName[0], v4l2.size_x, v4l2.size_y, v4l2.pixelFmt
			self.devs.append(v4l2)

		while 1:
			time.sleep(0.01)
			print time.time()

			#Poll cameras for updates
			for devInfo, dev in zip(self.devList, self.devs):
				data = dev.GetFrame(0)
				if data is None: continue
				dataStruc = data
				dataStruc.extend(devInfo)

				self.emit(QtCore.SIGNAL('webcam_frame'), dataStruc)

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


	def ProcessFrame(self, im):
		print "Frame update", im[1:]
		camId = im[4]
		if camId in self.currentFrames:
			self.scene.removeItem(self.currentFrames[camId])
			del self.currentFrames[camId]

		#self.scene.clear()

		im2 = QtGui.QImage(im[0], 640, 480, QtGui.QImage.Format_RGB888)
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


if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	camWorker = CamWorker()
	QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame"), mainWindow.ProcessFrame)
	camWorker.start() 

	sys.exit(app.exec_())

