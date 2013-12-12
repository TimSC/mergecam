import fisheye, csv
import math, pickle
import scipy.optimize as optimize
import scipy.misc as misc
import numpy as np

def SetCamVariables(cam1, cam2, x):
	cam2.cLat = x[0]
	cam2.cLon = x[1]

	cam1.a = x[2]
	cam1.b = x[3]
	cam1.c = x[4]
	cam1.d = x[5]
	cam1.e = x[6]
	cam2.a = x[2]
	cam2.b = x[3]
	cam2.c = x[4]
	cam2.d = x[5]
	cam2.e = x[6]

def ErrEval(x, cam1, cam2, cam1Pts, cam2Pts):
	SetCamVariables(cam1, cam2, x)

	cam1latLons = cam1.UnProj(cam1Pts)
	cam2latLons = cam2.UnProj(cam2Pts)

	err = 0.
	for ptcam1, ptcam2 in zip(cam1latLons, cam2latLons):
		err += abs(ptcam1[0] - ptcam2[0])
		err += abs(ptcam1[1] - ptcam2[1])
	print x, err
	return err

if __name__=="__main__":
	ptsData = csv.reader(open("correspond.csv"), delimiter="\t")
	cam1Pts, cam2Pts = [], []
	for li in ptsData:
		vals = map(float, li)
		cam1Pts.append((vals[:2]))
		cam2Pts.append((vals[2:4]))

	cam1 = fisheye.FishEye()
	cam2 = fisheye.FishEye()
	x0 = [cam2.cLat, cam2.cLon, cam1.a, cam1.b, cam1.c, cam1.d, cam1.e]

	if 0:
		ret = optimize.minimize(ErrEval, x0, args=(cam1, cam2, cam1Pts, cam2Pts), method="Powell")
		print ret.x
		SetCamVariables(cam1, cam2, ret.x)
		pickle.dump(cam1, open("cam1.dat", "wb"), protocol = -1)
		pickle.dump(cam2, open("cam2.dat", "wb"), protocol = -1)
	else:
		cam1 = pickle.load(open("cam1.dat", "rb"))
		cam2 = pickle.load(open("cam2.dat", "rb"))

	cam1latLons = cam1.UnProj(cam1Pts)

	for pt in cam1Pts:
		pt2 = cam1.UnProj([pt])
		rpt = cam1.Proj(pt2)
		print "chk", pt, rpt[0]

	exit(0)

	cam2latLons = cam2.UnProj(cam2Pts)
	#for i, (pt1, pt2) in enumerate(zip(cam1latLons, cam2latLons)):
	#	print i, (pt1, pt2)

	

	if 0:
		#Project back for reconstruction error
		pts2cam1 = cam1.Proj(cam2latLons)
		cam1errs = []
		for i, (pt1, pt2) in enumerate(zip(cam1Pts, pts2cam1)):
			dist = ((pt1[0]-pt2[0])**2. + (pt1[1]-pt2[1])**2.)**0.5
			print i, pt1, pt2, dist
			cam1errs.append(dist)
		cam1errs = np.array(cam1errs)
		print cam1errs.mean(), cam1errs.max()


	exit(0)

	outImg = np.zeros((1800/4, 3600/4, 3))
	outPts = []
	for x in range(outImg.shape[1]):
		for y in range(outImg.shape[0]):
			outPts.append((x, y))

	print "Calc transform, cam1"
	if 1:
		cam1PxPt = cam1.Proj(outPts)
		pickle.dump(cam1PxPt, open("cam1PxPt.dat", "wb"), protocol=-1)
	else:
		cam1PxPt = pickle.load(open("cam1PxPt.dat", "rb"))
	
	print "Apply transform, cam1"
	for inPt, outPt in zip(cam1PxPt, outPts):
		try:
			print outPt[1], outPt[0]
			outImg[outPt[1], outPt[0]] = inPt[int(round(inPt[1])), int(round(inPt[0]))]
		except IndexError:
			pass

	misc.imsave(outImg, "out1.png")

	print "Calc transform, cam2"
	#cam2latLons = cam2.Proj(outPts)


