
import scipy.misc as misc
import cv2
import rectilinear
import numpy as np
import matplotlib.pyplot as plt

def TransformKeyPoints(pts, hFov, vFov, imgW, imgH):
	rectilin = rectilinear.Rectilinear()
	pts = np.array(pts)
	centred = pts - (imgW/2., imgH/2.)
	scaled = centred / (imgW/2., imgH/2.)
	
	#print hFov, vFov, imgH, imgW
	
	hwidth = rectilin.UnProj(0., hFov / 2.)[0]
	hheight = rectilin.UnProj(vFov / 2., 0.)[1]
	normImg = scaled * (hwidth, hheight)
	polar = [rectilin.Proj(*pt) for pt in normImg]
	return polar

def VisualiseMatches(im1, im2, keypoints1, keypoints2, mat):
	combined = np.hstack((im1, im2))

	plt.imshow(combined)

	for dmat in mat:
		print dmat.distance, dmat.imgIdx, dmat.queryIdx, dmat.trainIdx
		ptA = keypoints1[dmat.queryIdx].pt
		ptB = keypoints2[dmat.trainIdx].pt

		if ptA[0] > 400:
			plt.plot((ptA[0], ptB[0] + im1.shape[1]), (ptA[1], ptB[1]))
	
	plt.show()



if __name__=="__main__":
	im1 = misc.imread("CIMG8588.JPG")
	im2 = misc.imread("CIMG8589.JPG")

	detector = cv2.FeatureDetector_create("ORB")
	descriptor = cv2.DescriptorExtractor_create("ORB")

	grey1 = cv2.cvtColor(im1,cv2.COLOR_BGR2GRAY)
	grey2 = cv2.cvtColor(im2,cv2.COLOR_BGR2GRAY)

	print "Extracting points of interest 1"
	keypoints1 = detector.detect(grey1)
	(keypoints1, descriptors1) = descriptor.compute(grey1, keypoints1)
	
	print "Extracting points of interest 2"
	keypoints2 = detector.detect(grey2)
	(keypoints2, descriptors2) = descriptor.compute(grey2, keypoints2)

	FLANN_INDEX_LSH = 6
	flann_params = dict(algorithm = FLANN_INDEX_LSH,
	                   table_number = 6, # 12
	                   key_size = 12,     # 20
	                   multi_probe_level = 1) #2

	matcher = cv2.FlannBasedMatcher(flann_params, {})
	mat = matcher.match(descriptors1, descriptors2)

	#for dmat in mat:
	#	print dmat.distance, dmat.imgIdx, dmat.queryIdx, dmat.trainIdx
		
	#Transform keypoints from rectilinear to polar space
	ptsPos1 = [a.pt for a in keypoints1]

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

	pts = TransformKeyPoints(ptsPos1, 49.0, 35.4, im1.shape[1], im1.shape[0])

	if 0:
		pts = np.array(pts)
		plt.plot(pts[:,1], -pts[:,0], '.')
		plt.show()

	VisualiseMatches(im1, im2, keypoints1, keypoints2, mat)

