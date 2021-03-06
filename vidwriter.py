
from PySide import QtGui, QtCore
import time, math

class VideoWriterWidget(QtGui.QFrame):
	def __init__(self, outFilesManagerIn, fullVersion):
		QtGui.QFrame.__init__(self)
		self.devOn = False
		self.outFilesManager = outFilesManagerIn
		self.startTime = None
		self.imgW = 800
		self.imgH = 600
		self.fullVersion = fullVersion

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		label = QtGui.QLabel("Video File Writer")
		self.toolbar.addWidget(label, 1)

		self.chooseFileButton = QtGui.QPushButton("Select Output File")
		self.toolbar.addWidget(self.chooseFileButton, 1)
		self.chooseFileButton.clicked.connect(self.ChooseFilePressed)

		#Create text box for file name
		self.fileLineLayout = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.fileLineLayout, 1)

		self.filenameEntry = QtGui.QLineEdit()
		self.filenameEntry.setText("out.mp4")
		self.fileLineLayout.addWidget(self.filenameEntry, 1)

		self.onButton = QtGui.QPushButton("Record")
		self.fileLineLayout.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		self.onButton.setEnabled(self.fullVersion)
		self.onButton.clicked.connect(self.ClickedOn)

		if not self.fullVersion:
			self.purchaseButton = QtGui.QPushButton("Purchase PRO Version to Record")
			self.widgetLayout.addWidget(self.purchaseButton)
			self.purchaseButton.pressed.connect(self.PurchasePressed)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

	def ClickedOn(self):

		if self.devOn:
			#Switch off
			self.devOn = False
			self.filenameEntry.setEnabled(True)
			self.chooseFileButton.setEnabled(True)
			self.outFilesManager.close(str(self.filenameEntry.text()))
		else:
			#Switch true
			self.devOn = True
			self.filenameEntry.setEnabled(False)
			self.chooseFileButton.setEnabled(True)
			try:
				fina = str(self.filenameEntry.text())
				self.outFilesManager.open(fina, self.imgW, self.imgH)
				#self.outFilesManager.set_video_codec(fina, "H264", 800000)
				#self.outFilesManager.enable_real_time_frame_rate(fina, True)
			except Exception as err:
				print err

		self.onButton.setChecked(self.devOn)

	def SendFrame(self, frame, meta, devName):
		if not self.devOn: return
		if meta['format'] != "RGB24": return

		#im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		#pix = QtGui.QPixmap(im2)
		#pixmap2 = pix.scaled(self.imgW, self.imgH)
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

	def ChooseFilePressed(self):

		choice = QtGui.QFileDialog.getSaveFileName(self,
    		caption="Select Output Video File", filter="mp4 Videos (*.mp4)")

		if len(choice[0]) > 0:
			self.filenameEntry.setText(choice[0])

	def VideoSizeChanged(self, w, h):
		
		#Stop if active
		if (w != self.imgW or h != self.imgH) and self.devOn:
			self.ClickedOn()

		self.imgW = w
		self.imgH = h

	def PurchasePressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://www.kinatomic.com/progurl/register.php"))


