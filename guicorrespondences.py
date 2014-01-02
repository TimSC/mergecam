from PySide import QtGui, QtCore

class GuiCorrespondences(QtGui.QFrame):

	def __init__(self, devManager):
		QtGui.QFrame.__init__(self)

		self.layout = QtGui.QHBoxLayout()
		self.setLayout(self.layout)

		self.layout.addWidget(QtGui.QLabel("test"))
