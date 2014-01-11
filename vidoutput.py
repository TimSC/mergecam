
from PySide import QtGui, QtCore

class VideoOutWidget(QtGui.QFrame):
	def __init__(self, videoOutManager):
		QtGui.QFrame.__init__(self)
		self.devOn = False
		self.videoOutManager = videoOutManager

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		self.widgetLayout.addWidget(QtGui.QLabel("Video Output Stream"))

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.devCombo = QtGui.QComboBox()
		self.toolbar.addWidget(self.devCombo, 1)
		for dev in self.videoOutManager.list_devices():
			self.devCombo.addItem(dev)

		self.onButton = QtGui.QPushButton("Transmit")
		self.toolbar.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

		self.standbyGraphic = None

	def ClickedOn(self):

		if self.devOn:
			self.devOn = False
			self.devCombo.setEnabled(True)
			self.videoOutManager.close(self.devId)
		else:
			self.devOn = True
			self.devId = self.devCombo.currentText()
			self.devCombo.setEnabled(False)
			self.videoOutManager.open(self.devId, "YUYV", 640, 480)

			if self.standbyGraphic is None:
				img = QtGui.QImage("standby_graphic.jpg")
				img2 = QtGui.QPixmap.fromImage(img)
				img3 = img2.scaled(640, 480)
				img4 = img3.toImage()
				self.standbyGraphic = img4.convertToFormat(QtGui.QImage.Format_RGB888)
			
			if self.standbyGraphic is not None:
				raw = self.standbyGraphic.constBits()
				self.videoOutManager.send_frame(self.devId, str(raw), "RGB24", 
					self.standbyGraphic.width(), self.standbyGraphic.height())

		self.onButton.setChecked(self.devOn)

	def SendFrame(self, frame, meta, devName):
		if not self.devOn: return
		#if meta['format'] != "RGB24": return

		#im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		#pix = QtGui.QPixmap(im2)
		#pixmap2 = pix.scaled(640, 480)
		#img = pixmap2.toImage()
		#img2 = img.convertToFormat(QtGui.QImage.Format_RGB888)
		#raw = img2.bits().asstring(img2.numBytes())
		self.videoOutManager.send_frame(self.devId, frame, "RGB24", 
			meta['width'], meta['height'])

	def Update(self):

		if self.cameraOn:
			if 0:
				#print len(data[0])
				self.emit(QtCore.SIGNAL('webcam_frame'), data[0], data[1], self.devId)
				self.UpdatePreview(data[0], data[1])

	def VideoSizeChanged(self, w, h):
		pass

