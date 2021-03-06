
from PySide import QtGui, QtCore
import time
import pycurl, threading, videolive

class HandleJpegData(object):
	def __init__(self):
		self.rxBuff = []
		self.stop = False

	def write(self, contentType, dat):
		self.rxBuff.append(dat)
		if self.stop:
			return 0 #Stop download
		else:
			return None

	def get_frame(self):

		if len(self.rxBuff) == 0:
			return None

		frameDat = self.rxBuff[0]
		self.rxBuff.pop(0)

		decodedFrame = bytearray()
		metaData = {}
		ret = videolive.DecodeAndResizeFrame("MJPEG", 0, 0, bytearray(frameDat), 
			"RGB24", 0, 0, decodedFrame, 
			metaData)

		return decodedFrame, metaData

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
		self.foundBoundary = 0

	def writeHeader(self, dat):
		print dat
		if dat[:13].lower()=="content-type:":

			valsplit = dat[13:].split(";")

			dataType = valsplit[0].strip()
			if dataType.lower() != "multipart/x-mixed-replace":
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
			#print eol, "'"+str(li[:100])+"'"

			self.rxBuff = self.rxBuff[eol+2:]
			if eol == 0 and self.foundBoundary:
				self.inBinarySection = True
				return

			if li == self.boundary: #Boundary mark
				self.foundBoundary = 1

			if li == "--"+self.boundary: #Two different styles of boundary marks
				self.foundBoundary = 1

			if li[:15].lower()=="content-length:":
				self.contentLength = int(li[15:].strip())
			if li[:13].lower()=="content-type:":
				self.contentType = li[13:].strip()

		if self.inBinarySection and self.contentLength is None:
			#If content length is not specified, look for the end of jpeg
			jpegEnd = '\xff\xd9'
			twoLineBreaks = jpegEnd+'\r\n\r\n'+self.boundary
			eol = self.rxBuff.find(twoLineBreaks)

			if eol >= 0:
				#print ":".join("{0:x}".format(ord(c)) for c in self.rxBuff[eol-10:eol+10])

				binData = self.rxBuff[:eol+2]
				self.callback(self.contentType, binData)

				self.rxBuff = self.rxBuff[eol+2:]
				self.contentLength = None
				self.inBinarySection = False
				self.contentType = None
				self.foundBoundary = 0

		if self.inBinarySection and self.contentLength is not None and len(self.rxBuff) >= self.contentLength:
			binData = self.rxBuff[:self.contentLength]
			self.callback(self.contentType, binData)

			self.rxBuff = self.rxBuff[self.contentLength:]
			self.contentLength = None
			self.inBinarySection = False
			self.contentType = None
			self.foundBoundary = 0

def Get(url, rx, incomingImages, userpass = None):
	while not incomingImages.stop:
		c = pycurl.Curl()
		c.setopt(pycurl.URL, str(url))
		if userpass is not None: c.setopt(pycurl.USERPWD, userpass)

		c.setopt(pycurl.WRITEFUNCTION, rx.writeBody)
		c.setopt(pycurl.HEADERFUNCTION, rx.writeHeader)  

		c.perform()

		#Prevent sending requests too often
		if not incomingImages.stop:
			time.sleep(1.)

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
	
	def __del__(self):
		print "Stop ip cam"
		if self.cameraOn:
			self.ClickedOn()

	def Stop(self):
		if self.cameraOn:
			self.ClickedOn()		

	def Update(self):
		if self.cameraOn and self.decoder is not None:
			if len(self.incomingImages.rxBuff) > 0:
				data = self.incomingImages.get_frame()
				if data is not None:
					#print "emit", self.devId, self.url
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
			self.incomingImages.stop = True
			self.ClearPreview()
		else:
			self.cameraOn = True
			self.incomingImages.stop = False
			self.decoder = DecodeXMixedReplace()
			self.decoder.callback = self.incomingImages.write
			self.thread = threading.Thread(group=None, target=Get, args=(self.url, self.decoder, self.incomingImages))
			self.thread.daemon = 1
			self.thread.start()

		#self.onButton.setChecked(self.cameraOn)

	def ClickedCheckBox(self):
		self.sourceToggled.emit(self.devId, self.checkbox.isChecked())

	def IsChecked(self):
		return self.checkbox.isChecked()

	def GetSaveParams(self):
		return {'url':self.url}
