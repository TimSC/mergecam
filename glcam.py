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
		for devName in self.devList:
			v4l2 = v4l2cap.V4L2()
			v4l2.Start(devName[0])
			self.devs.append(v4l2)

		while 1:
			time.sleep(0.01)

			#Poll cameras for updates
			for devInfo, dev in zip(self.devList, self.devs):
				data = dev.GetFrame(0)
				if data is None: continue
				print data[1:], devInfo
				


			#self.emit(QtCore.SIGNAL('webcam_frame(QImage)'), im)

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 
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
		print "Frame update", im
		pix = QtGui.QPixmap(im)
		self.scene.clear()
		self.scene.addPixmap(pix)


if __name__ == '__main__':

	app = QtGui.QApplication(sys.argv)

	mainWindow = MainWindow()

	camWorker = CamWorker()
	QtCore.QObject.connect(camWorker, QtCore.SIGNAL("webcam_frame(QImage)"), mainWindow.ProcessFrame)
	camWorker.start() 

	sys.exit(app.exec_())

