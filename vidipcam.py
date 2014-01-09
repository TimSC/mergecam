
from PySide import QtGui, QtCore
import time
import pycurl, threading, videolive

class HandleJpegData(object):
	def __init__(self):
		self.count = 0
		self.rxBuff = []

	def write(self, contentType, dat):
		#fi = open("test"+str(self.count)+".jpeg","wb")
		#fi.write(dat)
		#fi.close()
		self.rxBuff.append(dat)
		self.count += 1

	def get_frame(self):
		if len(self.rxBuff) == 0:
			return None

		frameDat = self.rxBuff[0]
		self.rxBuff.pop(0)

		decodedFrame = bytearray()
		ret = videolive.DecodeAndResizeFrame("MJPEG", 0, 0, bytearray(frameDat), "RGB24", 0, 0, decodedFrame)
		return decodedFrame, {'format': 'RGB24', 'height': 480, 'width': 640}

def HandleBinData(contentType, dat):
	print contentType, len(dat)

class DecodeXMixedReplace(object):
	def __init__(self):
		self.boundary = None
		self.rxBuff = ""
		self.inBinarySection = False
		self.contentLength = None
		self.contentType = None
		self.callback = HandleBinData

	def writeHeader(self, dat):
		if dat.startswith("Content-Type:"):
			valsplit = dat[13:].split(";")

			dataType = valsplit[0].strip()
			if dataType != "multipart/x-mixed-replace":
				raise Exception("Unexpected mime type: "+dataType)

			boundaryVal = valsplit[1].strip()
			boundarySplit = boundaryVal.split("=")
			self.boundary = boundarySplit[1]

	def writeBody(self, dat):
		self.rxBuff += dat
		eol = 0
		while eol >= 0 and not self.inBinarySection:
			eol = self.rxBuff.find("\r\n")
			if eol < 0: continue
			li = self.rxBuff[:eol]
			print eol, "'"+str(li)+"'"
			self.rxBuff = self.rxBuff[eol+2:]
			if eol == 0 and self.contentLength is not None:
				self.inBinarySection = True
			if li.startswith("Content-Length:"):
				self.contentLength = int(li[15:].strip())
			if li.startswith("Content-Type:"):
				self.contentType = li[13:].strip()

		if self.inBinarySection and len(self.rxBuff) >= self.contentLength:
			binData = self.rxBuff[:self.contentLength]
			self.callback(self.contentType, binData)

			self.rxBuff = self.rxBuff[self.contentLength:]
			self.contentLength = None
			self.inBinarySection = False
			self.contentType = None

def Get(url, rx, userpass = None):
	c = pycurl.Curl()
	print url
	c.setopt(pycurl.URL, str(url))
	if userpass is not None: c.setopt(pycurl.USERPWD, userpass)

	c.setopt(pycurl.WRITEFUNCTION, rx.writeBody)
	c.setopt(pycurl.HEADERFUNCTION, rx.writeHeader)  

	c.perform()


class IpCamWidget(QtGui.QFrame):
	webcamSignal = QtCore.Signal(bytearray, dict, str)
	sourceToggled = QtCore.Signal(str, int)

	def __init__(self, devId, friendlyName, camType, url):
		QtGui.QFrame.__init__(self)
		
		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		self.devId = devId
		self.cameraOn = False
		self.url = url
		self.friendlyName = "IP Camera"

		#Create toolbar
		self.toolbar = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.toolbar)

		self.checkbox = QtGui.QCheckBox()
		self.checkbox.setCheckState(QtCore.Qt.Checked)
		self.toolbar.addWidget(self.checkbox, 0)
		self.checkbox.clicked.connect(self.ClickedCheckBox)

		label = QtGui.QLabel(friendlyName)
		self.toolbar.addWidget(label, 1)

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
		self.incomingImages = HandleJpegData()

		#Start video
		self.ClickedOn()
	
	def Update(self):
		if self.cameraOn and self.decoder is not None:
			if len(self.incomingImages.rxBuff) > 0:
				data = self.incomingImages.get_frame()
				if data is not None:

					self.webcamSignal.emit(data[0], data[1], str(self.devId))
					self.UpdatePreview(data[0], data[1])

	def UpdatePreview(self, frame, meta):
		if meta['format'] != "RGB24": return

		img = QtGui.QImage(frame, meta['width'], meta['height'], QtGui.QImage.Format_RGB888)
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
			self.decoder = None
			self.thread = None
			self.ClearPreview()
		else:
			self.cameraOn = True
			self.decoder = DecodeXMixedReplace()
			self.decoder.callback = self.incomingImages.write
			self.thread = threading.Thread(group=None, target=Get, args=(self.url, self.decoder))
			self.thread.start()

		#self.onButton.setChecked(self.cameraOn)

	def ClickedCheckBox(self):
		self.sourceToggled.emit(self.devId, self.checkbox.isChecked())

	def IsChecked(self):
		return self.checkbox.isChecked()


