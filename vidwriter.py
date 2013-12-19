
from PyQt4 import QtGui, QtCore
import time, math

class VideoWriterWidget(QtGui.QFrame):
	def __init__(self, outFilesManagerIn):
		QtGui.QFrame.__init__(self)
		self.devOn = False
		self.outFilesManager = outFilesManagerIn
		self.startTime = None

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
			self.outFilesManager.close(str(self.filenameEntry.text()))
		else:
			#Switch true
			self.devOn = True
			self.filenameEntry.setReadOnly(True)
			try:
				fina = str(self.filenameEntry.text())
				self.outFilesManager.open(fina, 800, 600)
				#self.outFilesManager.set_video_codec(fina, "H264", 800000)
				#self.outFilesManager.enable_real_time_frame_rate(fina, True)
			except Exception as err:
				print err

		self.onButton.setChecked(self.devOn)

	def SendFrame(self, frame, meta, devName):
		if not self.devOn: return
		if meta['format'] != "RGB24": return

		print meta
		#im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		#pix = QtGui.QPixmap(im2)
		#pixmap2 = pix.scaled(640, 480)
		#img = pixmap2.toImage()
		#img2 = img.convertToFormat(QtGui.QImage.Format_RGB888)
		#raw = img2.bits().asstring(img2.numBytes())
		#Send frame to output
		
		timeNow = time.time()
		if self.startTime is None:
			self.startTime = timeNow
		elapseTime = timeNow - self.startTime

		self.outFilesManager.send_frame(str(self.filenameEntry.text()), 
			frame, "RGB24", 
			meta['width'], meta['height'],
			elapseTime)

	def Update(self):

		if self.cameraOn:
			if 0:
				#print len(data[0])
				self.emit(QtCore.SIGNAL('webcam_frame'), data[0], data[1], self.devId)
				self.UpdatePreview(data[0], data[1])

	def IsChecked(self):
		return self.checkbox.isChecked()

