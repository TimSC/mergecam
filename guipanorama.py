from PySide import QtGui, QtCore

class GuiPanorama(QtGui.QFrame):

	def __init__(self, correspondenceModel):
		QtGui.QFrame.__init__(self)

		self.correspondenceModel = correspondenceModel

		self.layout = QtGui.QHBoxLayout()
		self.setLayout(self.layout)

		self.scene = QtGui.QGraphicsScene()
		self.view = QtGui.QGraphicsView(self.scene)
		self.layout.addWidget(self.view)
		
	def SetFrame(self, frame, meta):

		#Update GUI with new frame
		if meta['format'] == "RGB24":
			self.scene.clear()
			im2 = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
			pix = QtGui.QPixmap(im2)

			gpm = QtGui.QGraphicsPixmapItem(pix)
			self.scene.addItem(gpm)

	def ProcessFrame(self, frame, meta, devName):
		self.SetFrame(frame, meta)
