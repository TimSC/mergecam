
from PyQt4 import QtGui, QtCore

class VideoWriterWidget(QtGui.QFrame):
	def __init__(self, outFilesManagerIn):
		QtGui.QFrame.__init__(self)
		self.devOn = False
		self.outFilesManager = outFilesManagerIn

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.toolbar.addWidget(self.checkbox, 0)

		label = QtGui.QLabel("Video Writer")
		self.toolbar.addWidget(label, 1)

		self.onButton = QtGui.QPushButton("On")
		self.toolbar.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		#Create text box for file name
		self.filenameEntry = QtGui.QLineEdit()
		self.filenameEntry.setText("out.mp4")
		self.widgetLayout.addWidget(self.filenameEntry, 1)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

	def ClickedOn(self):

		if self.devOn:
			#Switch off
			self.devOn = False
			self.filenameEntry.setReadOnly(False)
			self.outFilesManager.close(self.filenameEntry.text)
		else:
			#Switch true
			self.devOn = True
			self.filenameEntry.setReadOnly(True)
			self.outFilesManager.open(self.filenameEntry.text, 640, 480)

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
		#Send frame to output
		
		outManager.send_frame(self.filenameEntry.text, raw, "RGB24", meta['width'], meta['height'])

	def Update(self):

		if self.cameraOn:
			if 0:
				#print len(data[0])
				self.emit(QtCore.SIGNAL('webcam_frame'), data[0], data[1], self.devId)
				self.UpdatePreview(data[0], data[1])

	def IsChecked(self):
		return self.checkbox.isChecked()

