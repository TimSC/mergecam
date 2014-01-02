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

	def FindFriendlyName(self, devId):
		print "search", devId
		for devData in self.deviceList:
			if devData[0] != devId: continue
			if len(devData) >= 2:
				return devData[1]
		return devId

	def RefreshList(self):
		self.frameCombo.clear()
		for devId in self.correspondenceModel.devInputs:
			name = self.FindFriendlyName(devId)
			self.frameCombo.addItem(name)

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
