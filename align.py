
import scipy.misc as misc
import cv2, cv, os, pickle
import rectilinear
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

def VisualiseKeypoints(im, keypoints):
	plt.imshow(im, cmap = cm.Greys_r)
	pts = np.array([kp.pt for kp in keypoints])


	plt.plot(pts[:,0], pts[:,1], '.')
	
	plt.show()

def VisualiseMatches(im1, im2, keypoints1, keypoints2, mat, mask = None):
	combined = np.hstack((im1, im2))

	plt.imshow(combined)

	if mask is None:
		mask = np.ones((len(mat),))

	for dmat, ma in zip(mat, mask):
		#print dmat.distance, dmat.imgIdx, dmat.queryIdx, dmat.trainIdx
		if not ma: continue
		ptA = keypoints1[dmat.queryIdx].pt
		ptB = keypoints2[dmat.trainIdx].pt
		plt.plot((ptA[0], ptB[0] + im1.shape[1]), (ptA[1], ptB[1]))
	
	plt.show()

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

if __name__=="__main__":
	#im1 = misc.imread("CIMG8588.JPG")
	#im2 = misc.imread("CIMG8589.JPG")
	pairs = []

	l = "/home/tim/dev/glcamdata/house"
	filist = os.listdir(l)

	#Extract keypoints and descriptors
	keyPointsLi, descriptorsLi = [], []
	for i, fina in enumerate(filist):
		print "Extracting keypoints and descriptors", fina
		im1 = misc.imread(l+"/"+fina)
		keypoints1, descriptors1 = GetKeypointsAndDescriptors(im1)
		if len(keypoints1)==0:
			print "Warning: no keypoints found"
		keyPointsLi.append(keypoints1)
		descriptorsLi.append(descriptors1)

	#Calc homography between pairs
	for i, fina in enumerate(filist):
		for i2, fina2 in enumerate(filist):
			if i <= i2: continue
			print i, i2
			im1 = misc.imread(l+"/"+fina)
			im2 = misc.imread(l+"/"+fina2)

			keypoints1, descriptors1 = keyPointsLi[i], descriptorsLi[i]
			keypoints2, descriptors2 = keyPointsLi[i2], descriptorsLi[i2]
			if len(keypoints1) == 0 or len(keypoints2) == 0:
				print "No keypoints in photo"
				continue

			H, frac, inliers1, inliers2 = CalcHomographyForImagePair(keypoints1, descriptors1, keypoints2, descriptors2)
			homqual = HomographyQualityScore(H)
			#print "Homography", H
			print "Fraction used", frac
			print "Quality", homqual
			#print inliers1
			#print inliers2

			pairs.append((frac*homqual, fina, fina2, inliers1, inliers2, im1.shape, im2.shape, H))
		
	pairs.sort()
	pairs.reverse()
	pickle.dump(pairs, open("imgpairs.dat","wb"), protocol=-1)
	for pair in pairs:
		print pair

