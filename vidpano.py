
from PySide import QtGui, QtCore
import uuid
import cv2, cv, proj, math, random, time
import numpy as np
import scipy.optimize as optimize
import visualise, pano

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

	print "Convert to grey"
	grey1 = cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY)
	print "Conversion done"

	print "GetKeypoints"
	detector = cv2.FeatureDetector_create("ORB")
	#print detector.getParams()
	detector.setInt("nFeatures", 50)
	print "GetKeypoints done"

	print "Get descriptors"
	descriptor = cv2.DescriptorExtractor_create("BRIEF")
	#print "Extracting points of interest 1"
	#keypoints1 = detector.detect(grey1)
	keypoints1 = DetectAcrossImage(grey1, detector)
	#VisualiseKeypoints(grey1, keypoints1)
	(keypoints1, descriptors1) = descriptor.compute(grey1, keypoints1)
	print "Get descriptors done"

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

class CameraArrangement(object):
	def __init__(self):
		self.addedPhotos = {}
		self.camParams = None

	def AddAnchorPhoto(self, photoId, camModel):
		print "AddAnchorPhoto", photoId
		self.addedPhotos[photoId] = camModel

	def AddAndOptimiseFit(self, photoId, camModel, imgPairs, optRotation=False):
		print "OptimiseFit", photoId
		self.addedPhotos[photoId] = camModel

		x0 = [camModel.cLat, camModel.cLon, camModel.rot, 0., 0., 0., 0., 0.]
		for dof in range(1,len(x0)+1):
			ret = optimize.fmin_bfgs(self.Eval, x0[:dof], args=(photoId, imgPairs), gtol = 10., full_output=1)
			print ret
			if len(ret[0].shape) == 0:
				x0[0] = float(ret[0])
			else:
				for valNum, val in enumerate(list(ret[0])):
					x0[valNum] = val
	
		#Update camera parameters
		xfinal = ret[0]
		camToOpt = self.addedPhotos[photoId]
		camToOpt.cLat = xfinal[0]
		camToOpt.cLon = xfinal[1]
		camToOpt.rot = xfinal[2]

		for cam in self.addedPhotos.values():
			cam.SetCorrectionParams(xfinal[3], xfinal[4], xfinal[5])
			cam.d = xfinal[6]
			cam.e = xfinal[7]

	def Eval(self, vals, photoId, imgPairs, vis=0):

		camToOpt = self.addedPhotos[photoId]
		if len(vals)>0: camToOpt.cLat = vals[0]
		if len(vals)>1: camToOpt.cLon = vals[1]
		if len(vals)>2: camToOpt.rot = vals[2]

		for cam in self.addedPhotos.values():
			cama = None
			camb = None
			camc = None
			if len(vals)>3: cama = vals[3]
			if len(vals)>4: camb = vals[4]
			if len(vals)>5: camc = vals[5]

			cam.SetCorrectionParams(cama, camb, camc)
			if len(vals)>6: cam.d = vals[6]
			if len(vals)>7: cam.e = vals[7]

		err = 0.
		for pair in imgPairs:
			pairScore = pair[0]
			included1 = pair[1] in self.addedPhotos
			included2 = pair[2] in self.addedPhotos
			if not included1 or not included2: continue
			#print "Found pair", pair[:3]

			cam1 = self.addedPhotos[pair[1]]
			cam2 = self.addedPhotos[pair[2]]

			cam1latLons = cam1.UnProj(pair[3])
			cam2latLons = cam2.UnProj(pair[4])
			
			for ptcam1, ptcam2 in zip(cam1latLons, cam2latLons):
				err += abs(ptcam1[0] - ptcam2[0])
				err += abs(ptcam1[1] - ptcam2[1])

		print vals, err
		return err

	def NumPhotos(self):
		return len(self.addedPhotos)

	def SetCamParams(self, camParams):
		self.camParams = camParams

	def OptimiseCameraPositions(self, framePairs):

		if self.camParams is None:
			return None

		camProjFactory = None
		if self.camParams['proj'] == "rectilinear":
			camProjFactory = proj.Rectilinear
			projParams = {}
		if self.camParams['proj'] == "fisheye":
			camProjFactory = proj.FishEye
			projParams = {}
		assert camProjFactory is not None

		#Calibrate cameras
		#self.cameraArrangement = CameraArrangement(self.framePairs[0])
		#visobj = visualise.VisualiseArrangement()
		bestPair = 1	

		while bestPair is not None:# and len(self.cameraArrangement.addedPhotos) < 5:
			firstFrameSetPairs = framePairs[0]
			bestPair, newInd1, newInd2 = SelectPhotoToAdd(firstFrameSetPairs, self)
			print "SelectPhotoToAdd", bestPair, newInd1, newInd2
			if bestPair is None: continue
			print bestPair[:3], newInd1, newInd2
		
			photosToAdd = []
			photosMetaToAdd = []

			if not newInd1:
				print "Adding", bestPair[1]
				photosToAdd.append(bestPair[1])
				photosMetaToAdd.append(bestPair[5])
				
			if not newInd2:
				print "Adding", bestPair[2]
				photosToAdd.append(bestPair[2])
				photosMetaToAdd.append(bestPair[6])
			
			if 1:
				if self.NumPhotos() == 0 and len(photosToAdd) > 0:
					newCam = camProjFactory()
					newCam.imgW = photosMetaToAdd[0][1]
					newCam.imgH = photosMetaToAdd[0][0]
					self.AddAnchorPhoto(photosToAdd[0], newCam)
					photosToAdd.pop(0)
					photosMetaToAdd.pop(0)
				for pid, pmeta in zip(photosToAdd, photosMetaToAdd):
					#Add photos one by one to scene and optimise
					newCam = camProjFactory()
					newCam.imgW = pmeta[1]
					newCam.imgH = pmeta[0]				
					self.AddAndOptimiseFit(pid, newCam, firstFrameSetPairs, optRotation = True)

			for photoId in self.addedPhotos:
				photo = self.addedPhotos[photoId]
				print photoId, photo.cLat, photo.cLon
				#print "Proj test", photo.Proj([(0.,0.)])
				hfov = photo.UnProj([(0., photo.imgH * 0.5), (photo.imgW, photo.imgH * 0.5)])
				vfov = photo.UnProj([(photo.imgW * 0.5, 0.), (photo.imgW * 0.5, photo.imgH)])
				print "HFOV", math.degrees(hfov[1][1] - hfov[0][1])
				print "VFOV", math.degrees(vfov[1][0] - vfov[0][0])

			if 0:
				vis = visobj.Vis(self.calibrationFrames[0], self.calibrationMeta[0], self.framePairs[0], self.cameraArrangement)
				vis.save("vis{0}.png".format(len(self.cameraArrangement.addedPhotos)))

	def PrepareForPickle(self):
		for proj in self.addedPhotos.values():
			proj.PrepareForPickle()

def SelectPhotoToAdd(imgPairs, cameraArrangement):
	bestScore = None
	bestPair = None
	bestNewInd = None
	for pair in imgPairs:
		assert len(pair) == 8
		pairScore = pair[0]
		
		included1 = pair[1] in cameraArrangement.addedPhotos
		included2 = pair[2] in cameraArrangement.addedPhotos
		if len(cameraArrangement.addedPhotos) > 0:
			if included1 + included2 != 1: continue

		#print pairScore, pair[1:3], included1, included2
		if bestScore is None or pairScore > bestScore:
			bestScore = pairScore
			bestPair = pair

	if bestScore is None:
		return None, None, None

	return bestPair, included1, included2

def GetStrongestLinkForPhotoId(imgPairs, photoId):

	bestScore = None
	bestPair = None
	for pair in imgPairs:
		if photoId != pair[1] and photoId != pair[2]: continue
		if bestScore is None or pair[0] > bestScore:
			bestScore = pair[0]
			bestPair = pair
	return bestPair, bestScore


### Controlling widget

class PanoWidget(QtGui.QFrame):

	calibratePressed = QtCore.Signal()
	cameraParamsChanged = QtCore.Signal(dict)

	def __init__(self):
		QtGui.QFrame.__init__(self)

		self.devOn = True
		self.devId = uuid.uuid4()
		#self.canvas = QtGui.QImage(640*2, 480*2, QtGui.QImage.Format_RGB888)
		self.currentFrame = {}
		self.currentMeta = {}
		self.outBuffer = []
		self.framesRcvSinceOutput = set()
		self.framePairs = None

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		label = QtGui.QLabel("Panorama")
		label.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
		self.widgetLayout.addWidget(label, stretch = 0)

		#Create toolbar
		#self.toolbar = QtGui.QHBoxLayout()
		#self.widgetLayout.addLayout(self.toolbar, stretch = 0)

		self.presets = {"Generic Rectilinear": {"proj": "rectilinear", "hfov": 60., "a": 0., "b": 0., "c": 0., "d": 0., "e": 0.},
			"Generic Fisheye": {"proj": "fisheye", "hfov": 120., "a": 0., "b": 0., "c": 0., "d": 0., "e": 0.},
			"Genius Widecam 1050": {"proj": "fisheye", "hfov": 120., "a": 0.1, "b": 0.2, "c": 0.3, "d": 0.4, "e": 0.5},}

		#Create calibration controls
		self.presetCombo = QtGui.QComboBox()
		for presetId in self.presets:
			self.presetCombo.addItem(presetId)
		self.presetCombo.addItem("Custom")
		QtCore.QObject.connect(self.presetCombo, QtCore.SIGNAL('activated(const QString&)'), self.PresetActivated)
		self.widgetLayout.addWidget(self.presetCombo, 0)

		self.presetLayout = QtGui.QVBoxLayout()
		self.presetWidget = QtGui.QFrame()
		self.presetWidget.setFrameStyle(QtGui.QFrame.Box)
		self.presetWidget.setLayout(self.presetLayout)
		
		self.widgetLayout.addWidget(self.presetWidget, 0)

		self.projectionType = QtGui.QComboBox()
		self.projectionType.addItem("Rectilinear")
		self.projectionType.addItem("Fisheye")
		self.presetLayout.addWidget(self.projectionType, 0)

		self.paramLayout = QtGui.QGridLayout()
		self.presetLayout.addLayout(self.paramLayout)

		self.paramLayout.addWidget(QtGui.QLabel("Horizontal FOV"), 0, 0)
		self.paramLayout.addWidget(QtGui.QLabel("Lens a"), 1, 0)
		self.paramLayout.addWidget(QtGui.QLabel("Lens b"), 2, 0)
		self.paramLayout.addWidget(QtGui.QLabel("Lens c"), 3, 0)
		self.paramLayout.addWidget(QtGui.QLabel("Lens d"), 4, 0)
		self.paramLayout.addWidget(QtGui.QLabel("Lens e"), 5, 0)

		self.fovEdit = QtGui.QLineEdit()
		QtCore.QObject.connect(self.fovEdit, QtCore.SIGNAL('textEdited(const QString&)'), self.EditCustomButton)
		self.lensA = QtGui.QLineEdit()
		QtCore.QObject.connect(self.lensA, QtCore.SIGNAL('textEdited(const QString&)'), self.EditCustomButton)
		self.lensB = QtGui.QLineEdit()
		QtCore.QObject.connect(self.lensB, QtCore.SIGNAL('textEdited(const QString&)'), self.EditCustomButton)
		self.lensC = QtGui.QLineEdit()
		QtCore.QObject.connect(self.lensC, QtCore.SIGNAL('textEdited(const QString&)'), self.EditCustomButton)
		self.lensD = QtGui.QLineEdit()
		QtCore.QObject.connect(self.lensD, QtCore.SIGNAL('textEdited(const QString&)'), self.EditCustomButton)
		self.lensE = QtGui.QLineEdit()
		QtCore.QObject.connect(self.lensE, QtCore.SIGNAL('textEdited(const QString&)'), self.EditCustomButton)

		self.paramLayout.addWidget(self.fovEdit, 0, 1)
		self.paramLayout.addWidget(self.lensA, 1, 1)
		self.paramLayout.addWidget(self.lensB, 2, 1)
		self.paramLayout.addWidget(self.lensC, 3, 1)
		self.paramLayout.addWidget(self.lensD, 4, 1)
		self.paramLayout.addWidget(self.lensE, 5, 1)
		
		self.reviewCorrespondLayout = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.reviewCorrespondLayout, 0)
		self.reviewCorrespondCheckbox = QtGui.QCheckBox()
		self.reviewCorrespondLayout.addWidget(self.reviewCorrespondCheckbox, 0)
		self.reviewCorrespondLabel = QtGui.QLabel("Review correspondences before estimating cameras")
		self.reviewCorrespondLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
		self.reviewCorrespondLayout.addWidget(self.reviewCorrespondLabel, 0)

		self.calibrateControls = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.calibrateControls)	

		if 0:
			#Separate storage of calibration frames and optimisation
			self.onButton = QtGui.QPushButton("Store Calibration Frames")
			self.calibrateControls.addWidget(self.onButton, 0)
			QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedStoreCalibration)

			self.calibrationCount = QtGui.QLabel("0")
			self.calibrateControls.addWidget(self.calibrationCount, 1)

			self.onButton = QtGui.QPushButton("Cal")
			self.calibrateControls.addWidget(self.onButton, 0)
			QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedCalibrate)

		self.onButton = QtGui.QPushButton("Calibrate")
		self.calibrateControls.addWidget(self.onButton, 0)
		QtCore.QObject.connect(self.onButton, QtCore.SIGNAL('clicked()'), self.ClickedCalibrate)

		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

		#Initialise parameters
		ind = self.presetCombo.currentIndex()
		if ind >= 0:
			self.PresetActivated(self.presetCombo.itemText(ind))

	def PresetActivated(self, arg):
		arg = str(arg)
		print "PresetActivated", arg
		if arg not in self.presets: return

		selectedPreset = self.presets[arg]
		print selectedPreset

		#Update gui
		projInd = self.projectionType.findText(selectedPreset['proj'].capitalize())
		if projInd >= 0:
			self.projectionType.setCurrentIndex(projInd)

		self.fovEdit.setText(str(selectedPreset['hfov']))
		self.lensA.setText(str(selectedPreset['a']))
		self.lensB.setText(str(selectedPreset['b']))
		self.lensC.setText(str(selectedPreset['c']))
		self.lensD.setText(str(selectedPreset['d']))
		self.lensE.setText(str(selectedPreset['e']))

		self.CameraParamsChanged()

	def ClickedCalibrate(self):
		self.calibratePressed.emit()

	def EditCustomButton(self):
		ind = self.presetCombo.findText("Custom")
		if ind >= 0:
			self.presetCombo.setCurrentIndex(ind)
		self.CameraParamsChanged()

	def GetCamParams(self):
		#Get projection from gui
		selectedProj = self.projectionType.currentText()

		vfov = float(self.fovEdit.text())
		a = float(self.lensA.text())
		b = float(self.lensB.text())
		c = float(self.lensC.text())		
		d = float(self.lensD.text())
		e = float(self.lensE.text())

		camParams = {"proj": selectedProj.lower(), "hfov": vfov, "a": a, "b": b, "c": c, "d": d, "e": e}
		return camParams

	def CameraParamsChanged(self):
		self.cameraParamsChanged.emit(self.GetCamParams())

class FindCorrespondences(object):
	def __init__(self):
		self.devInputs = []
		self.currentFrames = {}
		self.currentMeta = {}
		self.calibrationFrames = []
		self.calibrationMeta = []

	def StoreCalibration(self):

		#Check frames from each camera are stored
		framesReady = True
		for devIn in self.devInputs:
			if devIn not in self.currentFrames:
				framesReady = False
		if not framesReady:
			print "Frames not ready"
			return
		
		#Store frame set for calibration use
		frameSet = []
		metaSet = []
		for devId in self.devInputs:
			frameSet.append(self.currentFrames[devId])
			metaSet.append(self.currentMeta[devId])

		self.calibrationFrames.append(frameSet)
		self.calibrationMeta.append(metaSet)

		#Update GUI
		#self.calibrationCount.setText(str(len(self.calibrationFrames)))

	def Calc(self):
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
		framePairs = []
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

			framePairs.append(pairsSet)

		return framePairs

	def AddSource(self, devId):
		if devId not in self.devInputs:
			self.devInputs.append(devId)
		print self.devInputs

	def RemoveSource(self, devId):
		if devId in self.devInputs:
			self.devInputs.remove(devId)
			if devId in self.currentFrames:
				del self.currentFrames[devId]
			if devId in self.currentMeta:
				del self.currentMeta[devId]
		print self.devInputs

	def ProcessFrame(self, frame, meta, devName):
		if devName not in self.devInputs: return
		self.currentFrames[devName] = frame
		self.currentMeta[devName] = meta




