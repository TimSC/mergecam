import numpy as np
import cv2
import scipy.misc as misc

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
	detector = cv2.FeatureDetector_create("BRISK")
	#print detector.getParams()
	#detector.setInt("nFeatures", 50)
	print "GetKeypoints done"

	print "Get descriptors"
	descriptor = cv2.DescriptorExtractor_create("FREAK")
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

#im1 = misc.imread("../demo/TrainA/test1.jpg")
#im2 = misc.imread("../demo/TrainB/test2.jpg")

im1 = misc.imread("../demo/StadiumA/test1a.png")
im2 = misc.imread("../demo/StadiumB/test2a.png")

kp1, des1 = GetKeypointsAndDescriptors(im1)
kp2, des2 = GetKeypointsAndDescriptors(im2)

if 0:
	# FLANN parameters
	FLANN_INDEX_KDTREE = 0
	index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
	search_params = dict(checks=50)   # or pass empty dictionary

	matcher = cv2.FlannBasedMatcher(index_params,search_params)
if 1:
	#matcher = cv2.BFMatcher(cv2.NORM_L2, 0)
	matcher = cv2.BFMatcher(cv2.NORM_HAMMING, 0)

print "match"
matches = matcher.knnMatch(des1,des2,k=2)

print "match done"

# Need to draw only good matches, so create a mask
matchesMask = [[0,0] for i in xrange(len(matches))]

# ratio test as per Lowe's paper
hit = 0
for i,(m,n) in enumerate(matches):
	if m.distance < 0.7*n.distance:
		matchesMask[i]=[1,0]
		hit += 1

imjoin = np.hstack((im1, im2))
import matplotlib.pyplot as plt
plt.imshow(imjoin)

print hit, len(matches)

for i, m in enumerate(matches):
	if matchesMask[i][0] == 0: continue
	bestm = m[0]

	pt1 = kp1[bestm.queryIdx].pt
	pt2 = kp2[bestm.trainIdx].pt
	plt.plot([pt1[0], pt2[0] + im1.shape[1]], [pt1[1], pt2[1]], '-')
plt.show()

