import numpy as np
import cv2

img1 = cv2.imread('../demo/TrainA/test1.jpg',0)          # queryImage
img2 = cv2.imread('../demo/TrainB/test2.jpg',0) # trainImage

# Initiate SIFT detector
sift = cv2.SIFT()

# find the keypoints and descriptors with SIFT
kp1, des1 = sift.detectAndCompute(img1,None)
kp2, des2 = sift.detectAndCompute(img2,None)

# FLANN parameters
FLANN_INDEX_KDTREE = 0
index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
search_params = dict(checks=50)   # or pass empty dictionary

flann = cv2.FlannBasedMatcher(index_params,search_params)

matches = flann.knnMatch(des1,des2,k=2)

# Need to draw only good matches, so create a mask
matchesMask = [[0,0] for i in xrange(len(matches))]

# ratio test as per Lowe's paper
for i,(m,n) in enumerate(matches):
    if m.distance < 0.7*n.distance:
        matchesMask[i]=[1,0]

imjoin = np.hstack((img1, img2))
import matplotlib.pyplot as plt
plt.imshow(imjoin)

for i, m in enumerate(matches):
	if matchesMask[i][0] == 0: continue
	bestm = m[0]

	pt1 = kp1[bestm.queryIdx].pt
	pt2 = kp2[bestm.trainIdx].pt
	plt.plot([pt1[0], pt2[0] + img1.shape[1]], [pt1[1], pt2[1]], '-')
plt.show()

