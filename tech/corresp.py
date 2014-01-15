
import numpy as np
import scipy.misc as misc
import cv2, random

def GetKeypointsAndDescriptors(im1):

	originalSize = im1.shape
	scaleImage = 0

	if scaleImage:
		targetw = 640
		targeth = 480

	if scaleImage and (originalSize[0] != targeth or originalSize[1] != targetw):
		print "Resizing image to find keypoints", originalSize
		im1 = cv2.resize(im1, (targeth, targetw))

	print "Convert to grey"
	grey1 = cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY)
	print "Conversion done"

	print "GetKeypoints"
	detector = cv2.FeatureDetector_create("ORB")
	#print detector.getParams()
	#detector.setInt("nFeatures", 50)
	print "GetKeypoints done"

	print "Get descriptors"
	descriptor = cv2.DescriptorExtractor_create("ORB")
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
		#print orpt, scpt
		kps = cv2.KeyPoint(scpt[0], scpt[1], kp.size, kp.angle, kp.response, kp.octave, kp.class_id)
		keypoints1scaled.append(kps)

	return (keypoints1scaled, descriptors1)

def FindRobustMatchesForImagePair(keypoints1, descriptors1, keypoints2, descriptors2, im1, im2):
	
	if 0:
		#Find corresponding points using FLANN
		FLANN_INDEX_KDTREE = 1
		FLANN_INDEX_LSH = 6
		flann_params = dict(algorithm = FLANN_INDEX_KDTREE)

		matcher = cv2.FlannBasedMatcher(flann_params, {})
		mat = matcher.match(descriptors1, descriptors2)
	
	if 1:

		#matcher = cv2.BFMatcher(cv2.NORM_L2, 1)
		matcher = cv2.BFMatcher(cv2.NORM_HAMMING, 1)
		mat = matcher.match(descriptors1, descriptors2)

	print "num points matched", len(mat)
	
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
		import matplotlib.pyplot as plt
		pts = np.array(ptsPos1)
		plt.plot(pts[:,0], -pts[:,1], '.')
		plt.show()

	#Transform keypoints from rectilinear to polar space
	#pts = TransformKeyPoints(ptsPos1, 49.0, 35.4, im1.shape[1], im1.shape[0])

	if 1:
		imjoin = np.hstack((im1, im2))
		import matplotlib.pyplot as plt
		plt.imshow(imjoin)
		pts = np.array(ptsPos1)

		for m in random.sample(mat,30):
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
	print "homoThresh", homoThresh
	H = cv2.findHomography(corresp1, corresp2, cv2.RANSAC, ransacReprojThreshold=homoThresh)
	#VisualiseMatches(im1, im2, keypoints1, keypoints2, mat, H[1])

	mask = np.array(H[1], dtype=np.bool)[:,0]
	corresp1Inliers = corresp1[mask]
	corresp2Inliers = corresp2[mask]

	return mask.mean(), corresp1Inliers, corresp2Inliers, corresp1, corresp2

if __name__ == "__main__":
	
	#im1 = misc.imread("../demo/StadiumA/test1a.png")
	#im2 = misc.imread("../demo/StadiumB/test2a.png")

	im1 = misc.imread("../demo/TrainA/test1.jpg")
	im2 = misc.imread("../demo/TrainB/test2.jpg")

	keypoints1, descriptors1 = GetKeypointsAndDescriptors(im1)
	keypoints2, descriptors2 = GetKeypointsAndDescriptors(im2)

	FindRobustMatchesForImagePair(keypoints1, descriptors1, keypoints2, descriptors2, im1, im2)

