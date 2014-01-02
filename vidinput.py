
from PyQt4 import QtGui, QtCore
import time

class SourceWidget(QtGui.QFrame):
	def __init__(self, devId, devManager, friendlyName):
		QtGui.QFrame.__init__(self)

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		self.devId = devId
		self.cameraOn = False
		self.devManager = devManager
		self.friendlyName = friendlyName

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.checkbox.setCheckState(QtCore.Qt.Checked)
		self.toolbar.addWidget(self.checkbox, 0)
		QtCore.QObject.connect(self.checkbox, QtCore.SIGNAL('clicked()'), self.ClickedCheckBox)

		label = QtGui.QLabel(friendlyName)
		self.toolbar.addWidget(label, 1)

		#self.onButton = QtGui.QPushButton("On")
		#self.toolbar.addWidget(self.onButton, 0)
		#self.onButton.setCheckable(True)
		#QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		#Create video preview
		img = QtGui.QImage(300, 200, QtGui.QImage.Format_RGB888)
		self.pic = QtGui.QLabel()
		self.pic.setMinimumSize(300,200)
		
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
		
		#self.onButton.setChecked(self.cameraOn)

	def ClickedCheckBox(self):
		self.emit(QtCore.SIGNAL('source_toggled'), self.devId, self.checkbox.isChecked())

	def IsChecked(self):
		return self.checkbox.isChecked()

class EmulateFixedRateVideoSource(SourceWidget):
	def __init__(self, devId, devManager, friendlyName):
		SourceWidget.__init__(self, devId, devManager, friendlyName)
		self.currentFrame = None
		self.currentMeta = None
		self.frameTimes = []

	def Update(self):
		
		if self.cameraOn:
			data = self.devManager.get_frame(self.devId)
			
			if data is not None:
				self.currentFrame = data[0]
				self.currentMeta = data[1]

			timeNow = time.time()
			if self.currentFrame is not None:
				send = False
				if len(self.frameTimes) < 2:
					send = True
				else:
					rate = len(self.frameTimes) / (timeNow - self.frameTimes[0])
					if rate < 30:
						send = True

				if send:
					self.UpdatePreview(self.currentFrame, self.currentMeta)
					self.emit(QtCore.SIGNAL('webcam_frame'), self.currentFrame, self.currentMeta, self.devId)
					self.frameTimes.append(timeNow)
					while len(self.frameTimes) > 50:
						self.frameTimes.pop(0)

			
