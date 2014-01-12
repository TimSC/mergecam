
from PySide import QtGui, QtCore
import time, os, random

class DemoCamWidget(QtGui.QFrame):
	webcamSignal = QtCore.Signal(bytearray, dict, str)
	sourceToggled = QtCore.Signal(str, int)

	def __init__(self, devId):
		QtGui.QFrame.__init__(self)
		
		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)
		self.lastFrame = time.time()
		self.imgs = None

		self.devId = devId
		self.cameraOn = False
		self.friendlyName = "Demo Camera"

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.checkbox.setCheckState(QtCore.Qt.Checked)
		self.toolbar.addWidget(self.checkbox, 0)
		self.checkbox.clicked.connect(self.ClickedCheckBox)

		label = QtGui.QLabel("Demo Camera")
		self.toolbar.addWidget(label, 1)

		self.camSelection = QtGui.QComboBox()
		demoList = os.listdir("demo")
		demoList.sort()
		for folder in demoList:
			if not os.path.isdir("demo"+os.sep+folder): continue
			self.camSelection.addItem(folder)
		self.camSelection.activated.connect(self.CameraSelectionChanged)
		self.widgetLayout.addWidget(self.camSelection, 0)

		#Create video preview
		img = QtGui.QImage(300, 200, QtGui.QImage.Format_RGB888)
		self.pic = QtGui.QLabel()
		self.pic.setMinimumSize(300,200)
		
		self.pic.setPixmap(QtGui.QPixmap.fromImage(img))
		self.widgetLayout.addWidget(self.pic, 0)

		self.setFrameStyle(QtGui.QFrame.Box)
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

		self.decoder = None
		self.thread = None

		#Start video
		self.ClickedOn()
		self.ClearPreview()
	
	def __del__(self):
		if self.cameraOn:
			self.ClickedOn()

	def Stop(self):
		if self.cameraOn:
			self.ClickedOn()		

	def Update(self):
		if self.cameraOn:
			#Cache images in memory
			if self.imgs is None:
				self.imgs = []
				camSelected = self.camSelection.currentText()
				folder = os.path.join("demo", camSelected)
				demoList = os.listdir(folder)				
				for fina1 in demoList:
					fina = folder + os.sep + fina1
					img = QtGui.QImage(fina)
					if img.format() != QtGui.QImage.Format_RGB888:
						img = img.convertToFormat(QtGui.QImage.Format_RGB888)
					self.imgs.append(img)

			timeNow = time.time()
			if timeNow - self.lastFrame > 0.1:

				if len(self.imgs) > 0:
					ind = random.randint(0, len(self.imgs)-1)
					img = self.imgs[ind]
					meta = {'width': img.size().width(), 'height': img.size().height(), "format": "RGB24"}
					self.UpdatePreview(img, img.size().width(), img.size().height())
					self.webcamSignal.emit(bytearray(img.constBits()), meta, str(self.devId))
				else:
					self.ClearPreview()

				self.lastFrame = timeNow

	def UpdatePreview(self, img, width, height):

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
			self.ClearPreview()
		else:
			self.cameraOn = True

		#self.onButton.setChecked(self.cameraOn)

	def ClickedCheckBox(self):
		self.sourceToggled.emit(self.devId, self.checkbox.isChecked())

	def IsChecked(self):
		return self.checkbox.isChecked()

	def CameraSelectionChanged(self):
		self.imgs = None

	def GetSaveParams(self):
		return {'cam':self.camSelection.currentText()}

