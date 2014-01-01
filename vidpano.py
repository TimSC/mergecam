
from PyQt4 import QtGui, QtCore
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
	def __init__(self, imgPairs):
		self.imgPairs = imgPairs
		self.addedPhotos = {}

	def AddAnchorPhoto(self, photoId, camModel):
		print "AddAnchorPhoto", photoId
		self.addedPhotos[photoId] = camModel

	def AddAndOptimiseFit(self, photoId, camModel, optRotation=False):
		print "OptimiseFit", photoId
		self.addedPhotos[photoId] = camModel

		x0 = [camModel.cLat, camModel.cLon, camModel.rot, 0., 0., 0., 0., 0.]
		for dof in range(1,len(x0)+1):
			ret = optimize.fmin_bfgs(self.Eval, x0[:dof], args=(photoId,), gtol = 10., full_output=1)
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

	def Eval(self, vals, photoId, vis=0):

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
		for pair in self.imgPairs:
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

def SelectPhotoToAdd(imgPairs, cameraArrangement):
	bestScore = None
	bestPair = None
	bestNewInd = None
	for pair in imgPairs:
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
	def __init__(self, devInputs):
		QtGui.QFrame.__init__(self)
		self.devOn = True
		self.devId = uuid.uuid4()
		self.devInputs = devInputs
		#self.canvas = QtGui.QImage(640*2, 480*2, QtGui.QImage.Format_RGB888)
		self.currentFrame = {}
		self.currentMeta = {}
		self.calibrationFrames = []
		self.calibrationMeta = []
		self.outBuffer = []
		self.framesRcvSinceOutput = set()
		self.framePairs = None
		self.cameraArrangement = None
		self.visobj = None

		self.widgetLayout = QtGui.QVBoxLayout()
		self.setLayout(self.widgetLayout)

		label = QtGui.QLabel("Panorama")
		label.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
		self.widgetLayout.addWidget(label, stretch = 0)

		#Create toolbar
		#self.toolbar = QtGui.QHBoxLayout()
		#self.widgetLayout.addLayout(self.toolbar, stretch = 0)

		#Create calibration controls

		self.projectionType = QtGui.QComboBox()
		self.projectionType.addItem("Rectilinear")
		self.projectionType.addItem("Fisheye")
		self.widgetLayout.addWidget(self.projectionType, 0)

		self.projectionParamLayout = QtGui.QHBoxLayout()
		self.widgetLayout.addLayout(self.projectionParamLayout)	

		self.projFlabel = QtGui.QLabel("F=")
		self.projectionParamLayout.addWidget(self.projFlabel, 0)

		self.projF = QtGui.QLineEdit()
		self.projectionParamLayout.addWidget(self.projF, 1)

		self.projKlabel = QtGui.QLabel("K=")
		self.projectionParamLayout.addWidget(self.projKlabel, 0)

		self.projK = QtGui.QLineEdit()
		self.projectionParamLayout.addWidget(self.projK, 1)

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
		self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

	def ClickedStoreCalibration(self):

		#Check frames from each camera are stored
		framesReady = True
		for devIn in self.devInputs:
			if devIn not in self.currentFrame:
				framesReady = False
		if not framesReady:
			print "Frames not ready"
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

		#Get projection from gui
		selectedProj = self.projectionType.currentText()
		camProjFactory = None
		if selectedProj == "Rectilinear":
			camProjFactory = proj.Rectilinear
			projParams = {}
		if selectedProj == "Fisheye":
			camProjFactory = proj.FishEye
			projParams = {}
		assert camProjFactory is not None

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

		assert len(self.framePairs) == 1

		#Calibrate cameras
		self.cameraArrangement = CameraArrangement(self.framePairs[0])
		#visobj = visualise.VisualiseArrangement()
		bestPair = 1	

		while bestPair is not None:# and len(self.cameraArrangement.addedPhotos) < 5:
			bestPair, newInd1, newInd2 = SelectPhotoToAdd(self.framePairs[0], self.cameraArrangement)
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
				if self.cameraArrangement.NumPhotos() == 0 and len(photosToAdd) > 0:
					newCam = camProjFactory()
					newCam.imgW = photosMetaToAdd[0][1]
					newCam.imgH = photosMetaToAdd[0][0]
					self.cameraArrangement.AddAnchorPhoto(photosToAdd[0], newCam)
					photosToAdd.pop(0)
					photosMetaToAdd.pop(0)
				for pid, pmeta in zip(photosToAdd, photosMetaToAdd):
					#Add photos one by one to scene and optimise
					newCam = camProjFactory()
					newCam.imgW = pmeta[1]
					newCam.imgH = pmeta[0]				
					self.cameraArrangement.AddAndOptimiseFit(pid, newCam, optRotation = True)

			for photoId in self.cameraArrangement.addedPhotos:
				photo = self.cameraArrangement.addedPhotos[photoId]
				print photoId, photo.cLat, photo.cLon
				#print "Proj test", photo.Proj([(0.,0.)])
				hfov = photo.UnProj([(0., photo.imgH * 0.5), (photo.imgW, photo.imgH * 0.5)])
				vfov = photo.UnProj([(photo.imgW * 0.5, 0.), (photo.imgW * 0.5, photo.imgH)])
				print "HFOV", math.degrees(hfov[1][1] - hfov[0][1])
				print "VFOV", math.degrees(vfov[1][0] - vfov[0][0])

			if 0:
				vis = visobj.Vis(self.calibrationFrames[0], self.calibrationMeta[0], self.framePairs[0], self.cameraArrangement)
				vis.save("vis{0}.png".format(len(self.cameraArrangement.addedPhotos)))

		print "Calculate final projection"		
		outProj = proj.EquirectangularCam()
		outProj.imgW = 800
		outProj.imgH = 600
		self.visobj = pano.PanoView(self.cameraArrangement, outProj)
		print "Done"

	def SendFrame(self, frame, meta, devName):
		if devName not in self.devInputs: return
		self.currentFrame[devName] = frame
		self.currentMeta[devName] = meta

		if not self.devOn: return
		if self.visobj is None: return

		if devName in self.framesRcvSinceOutput:
			#We have received this frame again; it is time to write output

			if self.cameraArrangement is not None:
				if 0:
					visobj = visualise.VisualiseArrangement()
					vis = visobj.Vis(self.currentFrame.values(), self.currentMeta.values(), self.framePairs[0], self.cameraArrangement)
					metaOut = {'width': vis.size[0], 'height': vis.size[1], 'format': 'RGB24'}
					self.outBuffer.append([vis.tostring(), metaOut])
				if 1:
					#print len(self.currentFrame), self.currentMeta
					startTime = time.time()
					visPixOut, visMetaOut = self.visobj.Vis(self.currentFrame.values(), self.currentMeta.values())
					print "Generated panorama in",time.time()-startTime,"sec"
					#self.visobj.Vis(self.currentFrame.values(), self.currentMeta.values())

					#visPixOut = bytearray([128 for i in range(800 * 600 * 3)])
					#visMetaOut = {"height": 600, "width": 800, "format": "RGB24"}
					
					#print len(visPixOut), visMetaOut
					self.outBuffer.append([bytearray(visPixOut), visMetaOut])

			self.framesRcvSinceOutput = set()

		self.framesRcvSinceOutput.add(devName)

	def Update(self):
		for result in self.outBuffer:
			self.emit(QtCore.SIGNAL('webcam_frame'), result[0], result[1], self.devId)
		self.outBuffer = []

	def AddSource(self, devId):
		if devId not in self.devInputs:
			self.devInputs.append(devId)
		print self.devInputs
		self.currentFrame = {}
		self.currentMeta = {}

	def RemoveSource(self, devId):
		if devId in self.devInputs:
			self.devInputs.remove(devId)
		print self.devInputs
		self.currentFrame = {}
		self.currentMeta = {}
