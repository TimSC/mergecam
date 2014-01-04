from PySide import QtGui, QtCore

class FrameView(QtGui.QWidget):
	selectionChanged = QtCore.Signal()

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
		self.controlPoints = []

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
		self.selectionChanged.emit()
		self.DrawFrame()

	def DrawFrame(self):
		ind = self.frameCombo.currentIndex()
		if len(self.correspondenceModel.calibrationFrames) < 1: return
		if ind < 0 or ind >= len(self.correspondenceModel.calibrationFrames[0]): return

		frame = self.correspondenceModel.calibrationFrames[0][ind]
		meta = self.correspondenceModel.calibrationMeta[0][ind]

		self.scene.clear()
		im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
		pix = QtGui.QPixmap(im2)

		gpm = QtGui.QGraphicsPixmapItem(pix)
		self.scene.addItem(gpm)

		pen = QtGui.QPen(QtCore.Qt.white, 1.0, QtCore.Qt.SolidLine);
		for pt in self.controlPoints:
			self.scene.addLine(pt[0]-5., pt[1], pt[0]+5., pt[1], pen)
			self.scene.addLine(pt[0], pt[1]-5., pt[0], pt[1]+5., pen)

	def CurrentIndex(self):
		return self.frameCombo.currentIndex()

	def CurrentText(self):
		return self.frameCombo.currentText()

	def SetControlPoints(self, pts):
		self.controlPoints = pts
		self.DrawFrame()

class GuiCorrespondences(QtGui.QFrame):

	def __init__(self, correspondenceModel):
		QtGui.QFrame.__init__(self)

		self.correspondenceModel = correspondenceModel
		self.framePairs = None

		self.layout = QtGui.QVBoxLayout()
		self.mainSplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
		self.setLayout(self.layout)
		self.layout.addWidget(self.mainSplitter)

		self.splitLayout = QtGui.QHBoxLayout()
		self.splitWidget = QtGui.QFrame()
		self.splitWidget.setLayout(self.splitLayout)
		self.mainSplitter.addWidget(self.splitWidget)

		self.leftView = FrameView(self.correspondenceModel)
		self.rightView = FrameView(self.correspondenceModel)

		self.leftView.selectionChanged.connect(self.SelectionChanged)
		self.rightView.selectionChanged.connect(self.SelectionChanged)

		self.splitLayout.addWidget(self.leftView)
		self.splitLayout.addWidget(self.rightView)

		self.table = QtGui.QTableWidget(3, 4, self)
		self.layout.addWidget(self.table)
	
		self.UpdateActiveDevices()

	def UpdateActiveDevices(self):
		self.leftView.RefreshList()
		self.rightView.RefreshList()

	def SetDeviceList(self, deviceList):
		self.leftView.deviceList = deviceList
		self.rightView.deviceList = deviceList
		self.UpdateActiveDevices()

	def UpdateFrames(self):
		self.leftView.DrawFrame()
		self.rightView.DrawFrame()

	def SetFramePairs(self, framePairs):
		self.framePairs = framePairs
		
	def SelectionChanged(self):
		indLeft = self.leftView.CurrentIndex()
		indRight = self.rightView.CurrentIndex()

		if self.framePairs is None or len(self.framePairs[0]) < 1: return
		firstSet = self.framePairs[0]

		found = 0
		for pair in firstSet:
			pairInd1 = pair[1]
			pairInd2 = pair[2]

			if pairInd1 == indLeft and pairInd2 == indRight:
				self.leftView.SetControlPoints(pair[3])
				self.rightView.SetControlPoints(pair[4])
				self.GenerateTable(pair[3], pair[4])
				found = 1

			if pairInd1 == indRight and pairInd2 == indLeft:
				self.leftView.SetControlPoints(pair[4])
				self.rightView.SetControlPoints(pair[3])
				self.GenerateTable(pair[4], pair[3])
				found = 1

		if not found:
			self.leftView.SetControlPoints([])
			self.rightView.SetControlPoints([])
			self.GenerateTable([], [])
		
	def GenerateTable(self, leftPts, rightPts):

		self.table.setRowCount(0)

		for lpt, rpt in zip(leftPts, rightPts):
			row = self.table.rowCount()
			self.table.setRowCount(row+1)

			newItem = QtGui.QTableWidgetItem(str(lpt[0]))
			self.table.setItem(row, 0, newItem)

			newItem = QtGui.QTableWidgetItem(str(lpt[1]))
			self.table.setItem(row, 1, newItem)

			newItem = QtGui.QTableWidgetItem(str(rpt[0]))
			self.table.setItem(row, 2, newItem)

			newItem = QtGui.QTableWidgetItem(str(rpt[1]))
			self.table.setItem(row, 3, newItem)

