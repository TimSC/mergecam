
from PySide import QtGui, QtCore
import uuid
import cv2, cv, proj, math, random, time, os
import numpy as np
import scipy.optimize as optimize
import pano, config

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

			#print str((wvals[w], hvals[h], patch.shape))
			kps = detector.detect(patch)
			for kp in kps:
				kp.pt = (kp.pt[0]+wvals[w]-margin, kp.pt[1]+hvals[h]-margin)
				out.append(kp)
	return out


def GetKeypointsAndDescriptors(im1):

	originalSize = im1.shape
	scaleImage = 0

	if scaleImage:
		targetw = 640
		targeth = 480

	if scaleImage and (originalSize[0] != targeth or originalSize[1] != targetw):
		print str(("Resizing image to find keypoints", originalSize))
		im1 = cv2.resize(im1, (targeth, targetw))

	print "Convert to grey"
	grey1 = cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY)
	print "Conversion done"

	print "GetKeypoints"
	detector = cv2.FeatureDetector_create("BRISK")
	#print str(detector.getParams())
	#detector.setInt("nFeatures", 50)
	print "GetKeypoints done"

	print "Get descriptors"
	descriptor = cv2.DescriptorExtractor_create("BRISK")
	#print "Extracting points of interest 1"
	keypoints1 = detector.detect(grey1)
	#keypoints1 = DetectAcrossImage(grey1, detector)
	#VisualiseKeypoints(grey1, keypoints1)
	(keypoints1, descriptors1) = descriptor.compute(grey1, keypoints1)
	print "Get descriptors done"

	if not scaleImage:
		return (keypoints1, descriptors1)

	keypoints1scaled = []
	for kp in keypoints1:
		orpt = kp.pt
		scpt = (kp.pt[0] * originalSize[0] / 480., kp.pt[1] * originalSize[1] / 640.)
		#print str((orpt, scpt))
		kps = cv2.KeyPoint(scpt[0], scpt[1], kp.size, kp.angle, kp.response, kp.octave, kp.class_id)
		keypoints1scaled.append(kps)

	return (keypoints1scaled, descriptors1)

def FindRobustMatchesForImagePair(keypoints1, descriptors1, keypoints2, descriptors2, im1, im2):
	
	if 0:
		#Find corresponding points using FLANN
		FLANN_INDEX_LSH = 6
		flann_params = dict(algorithm = FLANN_INDEX_LSH,
			               table_number = 6, # 12
			               key_size = 12,     # 20
			               multi_probe_level = 1) #2

		matcher = cv2.FlannBasedMatcher(flann_params, {})
		mat = matcher.match(descriptors1, descriptors2)
	
	if 1:
		matcher = cv2.BFMatcher(cv2.NORM_HAMMING, 0)
		mat = matcher.knnMatch(descriptors1, descriptors2, k=2)

	print str(("num points matched", len(mat)))

	#Filter based on ratios as per Lowe's paper
	#Use adaptive threshold to ensure there is at least 10 points
	filteredMatches = []
	ratioThreshold = 0.3
	while len(filteredMatches) < 10 and ratioThreshold < 1.:
		filteredMatches = []
		for i,(m,n) in enumerate(mat):
			if m.distance < ratioThreshold * n.distance:
				filteredMatches.append(m)
		if len(filteredMatches) < 10:
			ratioThreshold += 0.05
	mat = filteredMatches
	
	#for dmat in mat:
	#	print str((dmat.distance, dmat.imgIdx, dmat.queryIdx, dmat.trainIdx))
		
	ptsPos1 = [a.pt for a in keypoints1]
	ptsPos2 = [a.pt for a in keypoints2]

	if 0:
		for pt in ptsPos1:
			ptr = map(int,map(round,pt))
			col = (255,0,0)
			print str(ptr)
			cv2.circle(im1,tuple(ptr),2,col,-1)
		cv2.imshow('im1',im1)
		cv2.waitKey(0)
		cv2.destroyAllWindows()

	if 0:
		import matplotlib.pyplot as plt
		pts = np.array(ptsPos1)
		plt.plot(pts[:,0], -pts[:,1], '.')
		plt.show()

	#Transform keypoints from rectilinear to polar space
	#pts = TransformKeyPoints(ptsPos1, 49.0, 35.4, im1.shape[1], im1.shape[0])

	if 0:
		imjoin = np.hstack((im1, im2))
		import matplotlib.pyplot as plt
		plt.imshow(imjoin)
		pts = np.array(ptsPos1)

		for m in mat: #random.sample(mat,100):
			pt1 = keypoints1[m.queryIdx].pt
			pt2 = keypoints2[m.trainIdx].pt

			plt.plot([pt1[0], pt2[0] + im1.shape[1]], [pt1[1], pt2[1]], '-')
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
	homoThresh = ((im1.shape[1] + im2.shape[1]) * 0.5) * 0.05
	print str(("homoThresh", homoThresh))
	H = cv2.findHomography(corresp1, corresp2, cv2.RANSAC, ransacReprojThreshold=homoThresh)
	#VisualiseMatches(im1, im2, keypoints1, keypoints2, mat, H[1])
	mask = np.array(H[1], dtype=np.bool)[:,0]
	corresp1Inliers = corresp1[mask]
	corresp2Inliers = corresp2[mask]

	return mask.mean(), corresp1Inliers, corresp2Inliers, corresp1, corresp2

def CalcQualityForPair(inliers1, inliers2, corresp1, corresp2):
	if len(inliers1) < 3:
		return 0.

	inliers1homo = np.hstack((inliers1, np.ones(shape=(inliers1.shape[0], 1)))) #Convert to homogenious co
	inliers2homo = np.hstack((inliers2, np.ones(shape=(inliers2.shape[0], 1)))) #Convert to homogenious co
	corresp1homo = np.hstack((corresp1, np.ones(shape=(corresp1.shape[0], 1)))) #Convert to homogenious co
	corresp2homo = np.hstack((corresp2, np.ones(shape=(corresp2.shape[0], 1)))) #Convert to homogenious co

	transform = np.dot(inliers2homo.transpose(), np.linalg.pinv(inliers1homo.transpose()))
	#print str(("inv", transform))
	if 0:
		proj = np.dot(transform, inliers1homo.transpose())
		diff = proj - inliers2homo.transpose()
		errs = np.power(np.power(diff[:2,:].transpose(),2.).sum(axis=1),0.5)
		#print str(("inlier av err", errs.mean()))

		proj = np.dot(transform, corresp1homo.transpose())
		diff = proj - corresp2homo.transpose()
		errs2 = np.power(np.power(diff[:2,:].transpose(),2.).sum(axis=1),0.5)
		#print str(("corresp av err", errs2.mean()))

	#plt.plot(proj[0,:], proj[1,:],'x')
	#plt.plot(inliers2homo[:,0], inliers2homo[:,1],'o')
	#plt.show()

	#plt.hist(errs, bins=10)
	#plt.show()

	print str(transform)
	transformA = abs(1. - transform[0,0])
	transformB = abs(transform[1,0])
	transformC = abs(transform[0,1])
	transformD = abs(1. - transform[1,1])
	if transformA > 1.: transformA = 1.
	if transformB > 1.: transformB = 1.
	if transformC > 1.: transformC = 1.
	if transformD > 1.: transformD = 1.
	transformScore = (1.-transformA) * (1.-transformB) * (1.-transformC) * (1.-transformD)
	return transformScore
	#return 1. / errs.mean()

def StringToFloat(s):
    try:
        return float(s)
    except ValueError:
        return 0.

class CameraArrangement(object):
	def __init__(self):
		self.addedPhotos = {}
		self.camParams = None

	def Clear(self):
		self.addedPhotos = {}

	def PrepareForPickle(self):
		for proj in self.addedPhotos.values():
			proj.PrepareForPickle()

	def AddAnchorPhoto(self, photoId, camModel,
		progressThisIter, progressIterPlusOne, progressCallback):

		print str(("AddAnchorPhoto", photoId))
		if len(self.addedPhotos) > 0:
			raise Exception("Anchor photo should be first added")
		self.addedPhotos[photoId] = camModel

	def AddAndOptimiseFit(self, photoId, camModel, imgPairs, 
		progressThisIter, progressIterPlusOne, progressCallback, 
		optRotation=False):

		print str(("OptimiseFit", photoId))
		if len(self.addedPhotos) == 0:
			raise Exception("Anchor photo should be first added")
		if photoId in self.addedPhotos:
			raise Exception("Photo already added")
		self.addedPhotos[photoId] = camModel
		camModelParams = camModel.GetParams()

		x0 = [camModel.cLat, camModel.cLon, camModel.rot, camModelParams['a'], camModelParams['b'], 
			camModelParams['c'], camModelParams['d'], camModelParams['e']]
		print str(("x0", x0))
		for dof in range(1,len(x0)+1):
			#Progress calc
			print str((progressThisIter, progressIterPlusOne))
			if progressCallback is not None:
				progress = progressThisIter + (float(dof) / (len(x0)+1)) * (progressIterPlusOne - progressThisIter)
				progressCallback(progress)

			#Optimise Lens Model
			ret = optimize.fmin_bfgs(self.Eval, x0[:dof], args=(photoId, imgPairs), full_output=1, epsilon = 0.01)
			
			#print ret
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
		count = 0
		for pair in imgPairs:
			pairScore = pair[0]
			included1 = pair[1] in self.addedPhotos
			included2 = pair[2] in self.addedPhotos
			if not included1 or not included2: continue
			#print str(("Found pair", pair[:3]))

			cam1 = self.addedPhotos[pair[1]]
			cam2 = self.addedPhotos[pair[2]]

			#for pt1, pt2 in zip(pair[3], pair[4]):
			#	print str(("pt", pt1, pt2))

			cam1latLons = cam1.UnProj(pair[3])
			cam2latLons = cam2.UnProj(pair[4])
			
			for ptcam1, ptcam2 in zip(cam1latLons, cam2latLons):
				herr = abs(ptcam1[0] - ptcam2[0])
				verr = abs(ptcam1[1] - ptcam2[1])
				#print str(("err", herr, verr))
				err += herr
				err += verr
				count += 1

		#print str((vals, err / count))
		return err / count

	def NumPhotos(self):
		return len(self.addedPhotos)

	def SetCamParams(self, camParams):
		self.camParams = camParams

	def OptimiseCameraPositions(self, framePairs, progressCallback = None):

		if self.camParams is None:
			return None

		#Generate simple list of cam ids
		photoIds = set()
		for frameSet in framePairs:
			for pair in frameSet:
				photoIds.add(pair[1])
				photoIds.add(pair[2])
		print str(photoIds)

		camProjFactory = None
		if self.camParams['proj'] == "rectilinear":
			camProjFactory = proj.Rectilinear
		if self.camParams['proj'] == "fisheye":
			camProjFactory = proj.FishEye
		assert camProjFactory is not None

		firstFrameSetPairs = framePairs[0]

		#Cast coordinates to numpy array
		for pair in firstFrameSetPairs:
			pair[3] = np.array(pair[3])
			pair[4] = np.array(pair[4])
			pair[8] = np.array(pair[8])
			pair[9] = np.array(pair[9])

		#Calc quality of match pairs
		for pair in firstFrameSetPairs:
			print str(("Quality for pair", pair[:3]))
			print str(("old quality", pair[0]))
			quality = CalcQualityForPair(pair[3], pair[4], pair[8], pair[9])
			pair[0] = quality
			print str(("new quality", pair[0]))

		#Calibrate cameras
		#self.cameraArrangement = CameraArrangement(framePairs[0])
		#visobj = visualise.VisualiseArrangement()
		bestPair = 1

		while bestPair is not None:
			
			bestPair, newInd1, newInd2 = SelectPhotoToAdd(firstFrameSetPairs, self)
			#print str(("SelectPhotoToAdd", bestPair, newInd1, newInd2))
			if bestPair is None: continue
			print str((bestPair[:3], newInd1, newInd2))

			#Update progress calc
			print str(("len self.addedPhotos", len(self.addedPhotos)))
			progressThisIter = float(len(self.addedPhotos)) / len(photoIds)
			progressIterPlusOne = float(len(self.addedPhotos)+1) / len(photoIds)
			if progressCallback is not None:
				progressCallback(progressThisIter)
		
			photosToAdd = []
			photosMetaToAdd = []

			if not newInd1:
				print str(("Adding", bestPair[1]))
				photosToAdd.append(bestPair[1])
				photosMetaToAdd.append(bestPair[5])
				
			if not newInd2:
				print str(("Adding", bestPair[2]))
				photosToAdd.append(bestPair[2])
				photosMetaToAdd.append(bestPair[6])
			
			if 1:
				if self.NumPhotos() == 0 and len(photosToAdd) > 0:
					newCam = camProjFactory()
					newCam.SetParams(self.camParams)
					newCam.imgW = photosMetaToAdd[0][1]
					newCam.imgH = photosMetaToAdd[0][0]
					self.AddAnchorPhoto(photosToAdd[0], newCam, 
						progressThisIter, progressIterPlusOne, progressCallback)
					photosToAdd.pop(0)
					photosMetaToAdd.pop(0)

				for pid, pmeta in zip(photosToAdd, photosMetaToAdd):
					#Update progress
					progressThisIter = float(len(self.addedPhotos)) / len(photoIds)
					progressIterPlusOne = float(len(self.addedPhotos)+1) / len(photoIds)

					#Add photos one by one to scene and optimise
					newCam = camProjFactory()
					newCam.SetParams(self.camParams)
					newCam.imgW = pmeta[1]
					newCam.imgH = pmeta[0]				
					self.AddAndOptimiseFit(pid, newCam, firstFrameSetPairs, 
						progressThisIter, progressIterPlusOne, progressCallback, optRotation = True)
			
			for photoId in self.addedPhotos:
				photo = self.addedPhotos[photoId]
				print str((photoId, photo.cLat, photo.cLon))
				#print str(("Proj test", photo.Proj([(0.,0.)])))
				hfov = photo.UnProj([(0., photo.imgH * 0.5), (photo.imgW, photo.imgH * 0.5)])
				vfov = photo.UnProj([(photo.imgW * 0.5, 0.), (photo.imgW * 0.5, photo.imgH)])
				print str(("HFOV", math.degrees(hfov[1][1] - hfov[0][1])))
				print str(("VFOV", math.degrees(vfov[1][0] - vfov[0][0])))

			if 0:
				vis = visobj.Vis(self.calibrationFrames[0], self.calibrationMeta[0], framePairs[0], self.cameraArrangement)
				vis.save("vis{0}.png".format(len(self.cameraArrangement.addedPhotos)))

		print "Store camera parameters"
		firstCam = self.addedPhotos.values()[0]
		firstCamParams = firstCam.GetParams()
		projLens = "unknown"
		if isinstance(firstCam, proj.Rectilinear):
			projLens = "rectilinear"
		if isinstance(firstCam, proj.FishEye):
			projLens = "fisheye"
		firstCamParams['proj'] = projLens
		self.camParams = firstCamParams

	def PrepareForPickle(self):
		for proj in self.addedPhotos.values():
			proj.PrepareForPickle()

def SelectPhotoToAdd(imgPairs, cameraArrangement):
	bestScore = None
	bestPair = None
	bestNewInd = None
	bestInc1, bestInc2 = None, None
	for pair in imgPairs:

		pairScore = pair[0]
		
		included1 = pair[1] in cameraArrangement.addedPhotos
		included2 = pair[2] in cameraArrangement.addedPhotos
		print str(("pair check "+str(pair[:3])+" "+str(included1)+","+str(included2)))
		if len(cameraArrangement.addedPhotos) > 0:
			if included1 + included2 != 1: continue

		#print str((pairScore, pair[1:3], included1, included2))
		if bestScore is None or pairScore > bestScore:
			bestScore = pairScore
			bestPair = pair
			bestInc1 = included1
			bestInc2 = included2

	if bestScore is None:
		return None, None, None

	return bestPair, bestInc1, bestInc2

def GetStrongestLinkForPhotoId(imgPairs, photoId):

	bestScore = None
	bestPair = None
	for pair in imgPairs:
		if photoId != pair[1] and photoId != pair[2]: continue
		if bestScore is None or pair[0] > bestScore:
			bestScore = pair[0]
			bestPair = pair
	return bestPair, bestScore


### Lens parameter gui widget

class LensParamsWidget(QtGui.QFrame):

	calibratePressed = QtCore.Signal(int)
	cameraParamsChanged = QtCore.Signal(dict)

	def __init__(self):
		QtGui.QFrame.__init__(self)

		self.setContentsMargins(0, 0, 0, 0)
		self.devOn = True
		self.devId = uuid.uuid4()
		#self.canvas = QtGui.QImage(640*2, 480*2, QtGui.QImage.Format_RGB888)
		self.currentFrame = {}
		self.currentMeta = {}
		self.outBuffer = []
		self.framesRcvSinceOutput = set()

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		label = QtGui.QLabel("Select Preset Lens Parameters")
		label.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
		self.widgetLayout.addWidget(label, stretch = 0)

		#Create toolbar
		#self.toolbar = QtGui.QHBoxLayout()
		#self.widgetLayout.addLayout(self.toolbar, stretch = 0)

		self.presets = {"Generic Rectilinear": {"proj": "rectilinear", "hfov": 60., "a": 0., "b": 0., "c": 0., "d": 0., "e": 0.},
			"Generic Fisheye": {"proj": "fisheye", "hfov": 120., "a": 0., "b": 0., "c": 0., "d": 0., "e": 0.},
			"Genius Widecam 1050": {"proj": "fisheye", "hfov": 120., 
				"a": -0.0756995560702, 
				"b": -0.0028201661539, 
				"c": -0.00346306241764, 
				"d": 0.00462751409686, 
				"e": 0.},}

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

		self.projSelectAndHelp = QtGui.QHBoxLayout()
		self.presetLayout.addLayout(self.projSelectAndHelp, 0)

		self.projectionType = QtGui.QComboBox()
		self.projectionType.addItem("Rectilinear")
		self.projectionType.addItem("Fisheye")
		self.projectionType.activated.connect(self.EditCustomButton)
		self.projSelectAndHelp.addWidget(self.projectionType, 1)

		self.projHelpButton = QtGui.QPushButton("Help")
		self.projHelpButton.pressed.connect(self.ProjHelpPressed)
		self.projSelectAndHelp.addWidget(self.projHelpButton, 0)

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
		print str(("PresetActivated", arg))
		if arg not in self.presets: return

		selectedPreset = self.presets[arg]
		print str(selectedPreset)

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
		self.calibratePressed.emit(self.reviewCorrespondCheckbox.isChecked())

	def EditCustomButton(self):
		ind = self.presetCombo.findText("Custom")
		if ind >= 0:
			self.presetCombo.setCurrentIndex(ind)
		self.CameraParamsChanged()

	def GetCamParams(self):
		#Get projection from gui
		selectedProj = self.projectionType.currentText()

		hfov = StringToFloat(self.fovEdit.text())
		a = StringToFloat(self.lensA.text())
		b = StringToFloat(self.lensB.text())
		c = StringToFloat(self.lensC.text())		
		d = StringToFloat(self.lensD.text())
		e = StringToFloat(self.lensE.text())

		camParams = {"proj": selectedProj.lower(), "hfov": hfov, "a": a, "b": b, "c": c, "d": d, "e": e}
		return camParams

	def SetCamParams(self, params):
		self.lensA.setText(unicode(params['a']))
		self.lensB.setText(unicode(params['b']))
		self.lensC.setText(unicode(params['c']))
		self.lensD.setText(unicode(params['d']))
		self.lensE.setText(unicode(params['e']))

		ind = self.projectionType.findText(params['proj'].capitalize())
		if ind >= 0:
			self.projectionType.setCurrentIndex(ind)

		ind = self.presetCombo.findText("Custom")
		if ind >= 0:
			self.presetCombo.setCurrentIndex(ind)

	def CameraParamsChanged(self):
		self.cameraParamsChanged.emit(self.GetCamParams())

	def ProjHelpPressed(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.LENS_HELP_URL))

class FindCorrespondences(object):
	def __init__(self):
		self.devInputs = []
		self.currentFrames = {}
		self.currentMeta = {}
		self.calibrationFrames = []
		self.calibrationMeta = []

	def StoreCalibration(self):

		#Check frames from each camera are stored
		framesNotReady = []
		for devInfo in self.devInputs:
			if devInfo[0] not in self.currentFrames:
				framesNotReady.append(devInfo[0])
		if len(framesNotReady) != 0:
			print str(("Frames not ready", framesNotReady))
			return
		
		#Store frame set for calibration use
		frameSet = []
		metaSet = []
		for devInfo in self.devInputs:
			frameSet.append(self.currentFrames[devInfo[0]])
			metaSet.append(self.currentMeta[devInfo[0]])

		self.calibrationFrames.append(frameSet)
		self.calibrationMeta.append(metaSet)

		#Update GUI
		#self.calibrationCount.setText(str(len(self.calibrationFrames)))

	def PrepareForPickle(self):
		self.currentFrames = {}
		self.currentMeta = {}

	def Clear(self):
		self.calibrationFrames = []
		self.calibrationMeta = []

	def Calc(self):
		keypDescs = []
		imgSets = []

		#Extract interest points
		for photoSet, metaSet in zip(self.calibrationFrames, self.calibrationMeta):
			
			keypDescsSet = []
			imgs = []

			for frame, meta in zip(photoSet, metaSet):
				assert meta['format'] == "RGB24"
				arr = np.array(frame, dtype=np.uint8)
				source = arr.reshape((meta['height'], meta['width'], 3))

				#bitmap = cv.CreateImageHeader((source.shape[1], source.shape[0]), cv.IPL_DEPTH_8U, 3)
				#cv.SetData(bitmap, source.tostring(), source.dtype.itemsize * 3 * source.shape[1])

				keyp, desc = GetKeypointsAndDescriptors(source)
				keypDescsSet.append((keyp, desc))
				imgs.append(source)

			keypDescs.append(keypDescsSet)
			imgSets.append(imgs)

		#Calc homography between pairs
		framePairs = []
		for photoSet, metaSet, keypDescsSet, imgs in zip(self.calibrationFrames, self.calibrationMeta, keypDescs, imgSets):

			pairsSet = []
			
			for i, (frame1, meta1, (keyp1, desc1), img1) in enumerate(zip(photoSet, metaSet, keypDescsSet, imgs)):

				arr1 = np.array(frame1, dtype=np.uint8)
				im1 = arr1.reshape((meta1['height'], meta1['width'], 3))

				for i2, (frame2, meta2, (keyp2, desc2), img2) in enumerate(zip(photoSet, metaSet, keypDescsSet, imgs)):
					if i <= i2: continue
					print str(("Compare pair", i, i2))

					arr2 = np.array(frame2, dtype=np.uint8)
					im2 = arr2.reshape((meta2['height'], meta2['width'], 3))

					if len(keyp1) == 0 or len(keyp2) == 0:
						print "Warning: No keypoints in frame"
						continue

					print str(("num key pts", len(keyp1), len(keyp2)))

					frac, inliers1, inliers2, corresp1, corresp2 = FindRobustMatchesForImagePair(keyp1, desc1, 
						keyp2, desc2, img1, img2)
					
					quality = CalcQualityForPair(inliers1, inliers2, corresp1, corresp2)

					#print str(("Homography", H))
					print str(("Fraction used", frac))
					print str(("Quality score", quality))
					#print str(inliers1)
					#print inliers2

					qualityThreshold = 0.04
					if quality < qualityThreshold:
						print "discarding pair"
						pairsSet.append([None, i, i2, np.empty(shape=(0,0)), np.empty(shape=(0,0)), 
							im1.shape, im2.shape, None, np.empty(shape=(0,0)), np.empty(shape=(0,0))])
					else:
						pairsSet.append([None, i, i2, inliers1, inliers2, im1.shape, im2.shape, None, corresp1, corresp2])

			framePairs.append(pairsSet)

		return framePairs

	def SetActiveCams(self, devList):	
		self.devInputs = devList[:]

	def ProcessFrame(self, frame, meta, devName):
		self.currentFrames[devName] = frame
		self.currentMeta[devName] = meta




