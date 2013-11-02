
from PyQt4 import QtGui, QtCore
import uuid
import cv2, cv
import numpy as np

### Utility functions

def DetectAcrossImage(img, detector, targetPatchSize = 100.):

	wsteps = int(round(img.shape[1] / targetPatchSize))
	hsteps = int(round(img.shape[0] / targetPatchSize))
	if wsteps == 0: wsteps = 1
	if hsteps == 0: hsteps = 1

	wvals = np.linspace(0, img.shape[1], wsteps)
	hvals = np.linspace(0, img.shape[0], wsteps)
	margin = 30
	out = []
	for w in range(len(wvals)-1):
		for h in range(len(hvals)-1):	
			rowInd = np.arange(int(hvals[h]-margin),int(hvals[h+1]+margin),1)
			rowInd = np.mod(rowInd, img.shape[0])
			colInd = np.arange(int(wvals[w]-margin),int(wvals[w+1]+margin),1)
			colInd = np.mod(colInd, img.shape[1])
			patch = img[rowInd, :]
			patch = patch[:, colInd]
			assert patch.shape[0] > 0
			assert patch.shape[1] > 0

			#print wvals[w], hvals[h], patch.shape
			kps = detector.detect(patch)
			for kp in kps:
				kp.pt = (kp.pt[0]+wvals[w]-margin, kp.pt[1]+hvals[h]-margin)
				out.append(kp)
	return out


def GetKeypointsAndDescriptors(im1):
	detector = cv2.FeatureDetector_create("ORB")
	#print detector.getParams()
	detector.setInt("nFeatures", 50)
	descriptor = cv2.DescriptorExtractor_create("BRIEF")

	grey1 = cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY)

	#print "Extracting points of interest 1"
	#keypoints1 = detector.detect(grey1)
	keypoints1 = DetectAcrossImage(grey1, detector)
	#VisualiseKeypoints(grey1, keypoints1)
	(keypoints1, descriptors1) = descriptor.compute(grey1, keypoints1)
	return (keypoints1, descriptors1)

def CalcHomographyForImagePair(keypoints1, descriptors1, keypoints2, descriptors2):
	
	#Find corresponding points using FLANN
	FLANN_INDEX_LSH = 6
	flann_params = dict(algorithm = FLANN_INDEX_LSH,
	                   table_number = 6, # 12
	                   key_size = 12,     # 20
	                   multi_probe_level = 1) #2

	matcher = cv2.FlannBasedMatcher(flann_params, {})
	mat = matcher.match(descriptors1, descriptors2)

	#for dmat in mat:
	#	print dmat.distance, dmat.imgIdx, dmat.queryIdx, dmat.trainIdx
		
	ptsPos1 = [a.pt for a in keypoints1]
	ptsPos2 = [a.pt for a in keypoints2]

	if 0:
		for pt in ptsPos1:
			ptr = map(int,map(round,pt))
			col = (255,0,0)
			print ptr
			cv2.circle(im1,tuple(ptr),2,col,-1)
		cv2.imshow('im1',im1)
		cv2.waitKey(0)
		cv2.destroyAllWindows()

	if 0:
		pts = np.array(ptsPos1)
		plt.plot(pts[:,0], -pts[:,1], '.')
		plt.show()

	#Transform keypoints from rectilinear to polar space
	#pts = TransformKeyPoints(ptsPos1, 49.0, 35.4, im1.shape[1], im1.shape[0])

	if 0:
		pts = np.array(pts)
		plt.plot(pts[:,1], -pts[:,0], '.')
		plt.show()

	#VisualiseMatches(im1, im2, keypoints1, keypoints2, mat)

	#Generate list of corresponding points
	corresp1, corresp2 = [], []
	for dmat in mat:
		corresp1.append(keypoints1[dmat.queryIdx].pt)
		corresp2.append(keypoints2[dmat.trainIdx].pt)
	corresp1 = np.array(corresp1)
	corresp2 = np.array(corresp2)

	#Determine homography using ransac
	H = cv2.findHomography(corresp1, corresp2, cv2.RANSAC, ransacReprojThreshold=20.)
	#VisualiseMatches(im1, im2, keypoints1, keypoints2, mat, H[1])
	mask = np.array(H[1], dtype=np.bool)[:,0]
	corresp1Inliers = corresp1[mask]
	corresp2Inliers = corresp2[mask]

	return H[0], mask.mean(), corresp1Inliers, corresp2Inliers

def HomographyQualityScore(hom):
	cost = [abs(hom[0,0]- 1.)]
	cost.append(abs(hom[1,1]- 1.))
	cost.append(abs(hom[1,0]))
	cost.append(abs(hom[0,1]))
	costsum = np.array(cost).sum()
	if costsum == 0.:
		return 1000.
	return 1./costsum


### Controlling widget

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

		self.onButton = QtGui.QPushButton("Cal")
		self.calibrateControls.addWidget(self.onButton, 0)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedCalibrate)

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

	def ClickedCalibrate(self):
		self.keypDescs = []

		#Extract interest points
		for photoSet, metaSet in zip(self.calibrationFrames, self.calibrationMeta):
			keypDescsSet = []

			for frame, meta in zip(photoSet, metaSet):
				assert meta['format'] == "RGB24"
				arr = np.array(frame, dtype=np.uint8)
				source = arr.reshape((meta['height'], meta['width'], 3))

				#bitmap = cv.CreateImageHeader((source.shape[1], source.shape[0]), cv.IPL_DEPTH_8U, 3)
				#cv.SetData(bitmap, source.tostring(), source.dtype.itemsize * 3 * source.shape[1])

				keyp, desc = GetKeypointsAndDescriptors(source)
				keypDescsSet.append((keyp, desc))

			self.keypDescs.append(keypDescsSet)

		#Calc homography between pairs
		self.framePairs = []
		for photoSet, metaSet, keypDescsSet in zip(self.calibrationFrames, self.calibrationMeta, self.keypDescs):

			pairsSet = []
			
			for i, (frame1, meta1, (keyp1, desc1)) in enumerate(zip(photoSet, metaSet, keypDescsSet)):

				arr1 = np.array(frame1, dtype=np.uint8)
				im1 = arr1.reshape((meta1['height'], meta1['width'], 3))

				for i2, (frame2, meta2, (keyp2, desc2)) in enumerate(zip(photoSet, metaSet, keypDescsSet)):
					if i <= i2: continue
					print "Compare pair", i, i2

					arr2 = np.array(frame2, dtype=np.uint8)
					im2 = arr2.reshape((meta2['height'], meta2['width'], 3))

					if len(keyp1) == 0 or len(keyp2) == 0:
						print "Warning: No keypoints in frame"
						continue

					H, frac, inliers1, inliers2 = CalcHomographyForImagePair(keyp1, desc1, keyp2, desc2)
					homqual = HomographyQualityScore(H)
					#print "Homography", H
					print "Fraction used", frac
					print "Quality", homqual
					#print inliers1
					#print inliers2

					pairsSet.append((frac*homqual, i, i2, inliers1, inliers2, im1.shape, im2.shape, H))

			self.framePairs.append(pairsSet)



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

