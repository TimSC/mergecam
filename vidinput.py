
from PyQt4 import QtGui, QtCore

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
		self.toolbar.addWidget(self.checkbox, 0)

		label = QtGui.QLabel(friendlyName)
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
		
		self.onButton.setChecked(self.cameraOn)

	def ClickedUse(self):
		if not self.cameraOn:
			self.ClickedOn()

		self.emit(QtCore.SIGNAL('use_source_clicked'), self.devId)

	def IsChecked(self):
		return self.checkbox.isChecked()
