from PySide import QtGui, QtCore

class FrameView(QtGui.QWidget):
	def __init__(self, correspondenceModel):
		QtGui.QWidget.__init__(self)

		self.correspondenceModel = correspondenceModel
		self.deviceList = []

		self.layout = QtGui.QVBoxLayout()
		self.setLayout(self.layout)

		self.frameCombo = QtGui.QComboBox()
		self.layout.addWidget(self.frameCombo)
		QtCore.QObject.connect(self.frameCombo, QtCore.SIGNAL('activated(int)'), self.FrameChanged)

		self.scene = QtGui.QGraphicsScene()
		self.view = QtGui.QGraphicsView(self.scene)
		self.layout.addWidget(self.view, 1)

	def FindFriendlyName(self, devId):
		print "search", devId
		for devData in self.deviceList:
			if devData[0] != devId: continue
			if len(devData) >= 2:
				return devData[1]
		return devId

	def RefreshList(self):
		self.frameCombo.clear()
		devList = self.correspondenceModel.devInputs
		for devId in devList:
			name = self.FindFriendlyName(devId)
			self.frameCombo.addItem(name)

	def FrameChanged(self, ind = None):
		if ind is None:
			ind = self.frameCombo.currentIndex()

		if len(self.correspondenceModel.calibrationFrames) < 1: return
		if ind < 0 or ind >= len(self.correspondenceModel.calibrationFrames[0]): return

		self.DrawScene(self.correspondenceModel.calibrationFrames[0][ind], 
			self.correspondenceModel.calibrationMeta[0][ind])

	def DrawScene(self, frame, meta):
		self.scene.clear()
		im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap(im2)

		gpm = QtGui.QGraphicsPixmapItem(pix)
		self.scene.addItem(gpm)

class GuiCorrespondences(QtGui.QFrame):

	def __init__(self, correspondenceModel):
		QtGui.QFrame.__init__(self)

		self.correspondenceModel = correspondenceModel

		self.layout = QtGui.QHBoxLayout()
		self.mainSplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
		self.setLayout(self.layout)
		self.layout.addWidget(self.mainSplitter)

		self.splitLayout = QtGui.QHBoxLayout()
		self.splitWidget = QtGui.QFrame()
		self.splitWidget.setLayout(self.splitLayout)
		self.mainSplitter.addWidget(self.splitWidget)

		self.tableFrame = QtGui.QFrame()
		self.tableLayout = QtGui.QHBoxLayout()
		self.tableFrame.setLayout(self.tableLayout)
		self.mainSplitter.addWidget(self.tableFrame)

		self.leftView = FrameView(self.correspondenceModel)
		self.rightView = FrameView(self.correspondenceModel)

		self.splitLayout.addWidget(self.leftView)
		self.splitLayout.addWidget(self.rightView)
		self.tableLayout.addWidget(QtGui.QLabel("Table"))

		self.UpdateActiveDevices()

	def UpdateActiveDevices(self):
		self.leftView.RefreshList()
		self.rightView.RefreshList()

	def SetDeviceList(self, deviceList):
		self.leftView.deviceList = deviceList
		self.rightView.deviceList = deviceList
		self.UpdateActiveDevices()

	def UpdateFrames(self):
		self.leftView.FrameChanged()
		self.rightView.FrameChanged()

