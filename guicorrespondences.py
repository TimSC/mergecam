from PySide import QtGui, QtCore

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

		self.splitLayout.addWidget(QtGui.QLabel("Left"))
		self.splitLayout.addWidget(QtGui.QLabel("Right"))
		self.tableLayout.addWidget(QtGui.QLabel("Table"))
