
from PyQt4 import QtGui, QtCore
import uuid

class PanoWidget(QtGui.QFrame):
	def __init__(self, devInputs):
		QtGui.QFrame.__init__(self)
		self.devOn = False
		self.devId = uuid.uuid4()
		self.devInputs = devInputs
		self.canvas = QtGui.QImage(640*2, 480*2, QtGui.QImage.Format_RGB888)
		self.currentFrame = {}
		self.currentMeta = {}
		self.calibrationFrames = []
		self.calibrationMeta = []
		self.outBuffer = []

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.toolbar.addWidget(self.checkbox, 0)

		label = QtGui.QLabel("Panorama")
		self.toolbar.addWidget(label, 1)

		#Create calibration controls

		self.calibrateControls = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.calibrateControls)

		self.onButton = QtGui.QPushButton("Store Calibration Frames")
		self.calibrateControls.addWidget(self.onButton, 0)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedStoreCalibration)

		self.calibrationCount = QtGui.QLabel("0")
		self.calibrateControls.addWidget(self.calibrationCount, 1)

		#Create view controls

		self.viewControls = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.viewControls)

		self.onButton = QtGui.QPushButton("On")
		self.viewControls.addWidget(self.onButton, 0)
		self.onButton.setCheckable(True)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedOn)

		self.useButton = QtGui.QPushButton("Use")
		self.viewControls.addWidget(self.useButton, 0)
		QtCore.QObject.connect(self.useButton, QtCore.SIGNAL('clicked()'), self.ClickedUse)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

	def ClickedOn(self):

		if self.devOn:
			self.devOn = False
		else:
			self.devOn = True
		print self.devOn
		self.onButton.setChecked(self.devOn)

	def ClickedStoreCalibration(self):

		if not self.devOn:
			self.ClickedOn()

		#Check frames from each camera are stored
		framesReady = True
		for devIn in self.devInputs:
			if devIn not in self.currentFrame:
				framesReady = False
		if not framesReady:
			return
		
		#Store frame set for calibration use
		frameSet = []
		metaSet = []
		for devId in self.currentFrame:
			frameSet.append(self.currentFrame[devId])
			metaSet.append(self.currentMeta[devId])

		self.calibrationFrames.append(frameSet)
		self.calibrationMeta.append(metaSet)

		#Update GUI
		self.calibrationCount.setText(str(len(self.calibrationFrames)))


	def SendFrame(self, frame, meta, devName):

		self.currentFrame[devName] = frame
		self.currentMeta[devName] = meta

		if not self.devOn: return

		if 0:
			if devName not in self.devInputs: return
			devIndex = self.devInputs.index(devName)
			x = devIndex / 2
			y = devIndex % 2

			img = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		
			painter = QtGui.QPainter(self.canvas)
			painter.setRenderHint(QtGui.QPainter.Antialiasing)
			painter.drawImage(640 * x, 480 * y, img)
			del painter

			if devName in self.framesRcvSinceOutput:
				#We have received this frame again; it is time to write output
				raw = self.canvas.bits().asstring(self.canvas.numBytes())
				metaOut = {'width': self.canvas.width(), 'height': self.canvas.height(), 'format': 'RGB24'}
				self.outBuffer.append([raw, metaOut])
				self.framesRcvSinceOutput = set()

			self.framesRcvSinceOutput.add(devName)

	def Update(self):
		for result in self.outBuffer:
			self.emit(QtCore.SIGNAL('webcam_frame'), result[0], result[1], self.devId)
		self.outBuffer = []

	def ClickedUse(self):
		if not self.devOn:
			self.ClickedOn()

		self.emit(QtCore.SIGNAL('use_source_clicked'), self.devId)

	def IsChecked(self):
		return self.checkbox.isChecked()

