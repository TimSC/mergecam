
import csv, math
import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize as opt

def MapToFloat(nums):
	out = []
	for v in nums:
		try:
			out.append(float(v))
		except ValueError:
			out.append(None)
	return out

def ReadCoord(fina):
	csvdata = csv.reader(fina)
	csvdata = [li for li in csvdata]

	#Remove top row
	csvdata.pop(0)
	out = []

	for li in csvdata:
		li.pop(0)
		xs = MapToFloat(li[0::2])
		ys = MapToFloat(li[1::2])
		row = zip(xs,ys)
		out.append(row)
	return out

class PatternModel(object):
	def __init__(self, screenDist, squareSize):
		self.screenDist = screenDist
		self.squareSize = squareSize

	def GetPoint(self, row, col):
		rowOff = row - self.centr
		colOff = col - self.centc

		x = rowOff + self.squareSize * self.patternShift[0] + colOff * self.squareSize
		y = rowOff + self.squareSize * self.patternShift[1] + rowOff * self.squareSize

		optAxisDist = (x**2. + y**2.)**0.5

		theta = math.atan2(optAxisDist, self.screenDist)
		ang = math.atan2(x, y)
		return theta, ang

class LensFishEyeStereographicModel(object):
	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h

	def Proj(self, theta, ang):
		r = 2 * self.f * math.tan(theta / 2.)
		imx = 0.5 * self.w + math.sin(ang) * r
		imy = 0.5 * self.h + math.cos(ang) * r
		return imx, imy

class LensFishEyeHybridModel(object):
	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h
		self.k = 0.75

	def Proj(self, theta, ang):
		r = self.f * math.tan(self.k*theta)
		imx = 0.5 * self.w + math.sin(ang) * r
		imy = 0.5 * self.h + math.cos(ang) * r
		return imx, imy

	def GetParams(self):
		return self.f, self.k

	def SetParams(self, p):
		self.f = p[0]
		self.k = p[1]

class LensFishEyeEquidistantModel(object):
	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h

	def Proj(self, theta, ang):
		r = self.f * math.tan(theta)
		imx = 0.5 * self.w + math.sin(ang) * r
		imy = 0.5 * self.h + math.cos(ang) * r
		return imx, imy

class LensFishEquisolidAngleModel(object):
	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h

	def Proj(self, theta, ang):
		r = 2 * self.f * math.sin(theta / 2.)
		imx = 0.5 * self.w + math.sin(ang) * r
		imy = 0.5 * self.h + math.cos(ang) * r
		return imx, imy

class LensOrthographicModel(object):
	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h

	def Proj(self, theta, ang):
		r = self.f * math.sin(theta)
		imx = 0.5 * self.w + math.sin(ang) * r
		imy = 0.5 * self.h + math.cos(ang) * r
		return imx, imy


def VisualisePoints(patternModel, corners, lens):
	
	actualPts = []
	predPts = []

	for r, row in enumerate(corners):
		for c, pos in enumerate(row):
			if pos[0] is None: continue

			testPos = patternModel.GetPoint(r, c)
			testProj = lens.Proj(*testPos)
			
			#print testProj, pos
			actualPts.append(pos)
			predPts.append(testProj)

	actualPts = np.array(actualPts)
	predPts = np.array(predPts)

	plt.plot(actualPts[:,0], actualPts[:,1], 'o')
	plt.plot(predPts[:,0], predPts[:,1], 'x')
	plt.show()

def Eval(params, patternModel, lens):
	errs = []
	lens.SetParams(params)
	print params

	for r, row in enumerate(corners):
		for c, pos in enumerate(row):
			if pos[0] is None: continue

			testPos = patternModel.GetPoint(r, c)
			testProj = lens.Proj(*testPos)
			
			#print testProj, pos
			err = ((testProj[0]-pos[0])**2.+(testProj[1]-pos[1])**2.)**0.5
			errs.append(err)
	return sum(errs) / len(errs)

if __name__ == "__main__":
	corners = ReadCoord(open("genius.csv"))

	imsize = (1280, 1024)
	cent = (imsize[0]/2., imsize[1]/2.)
	
	#Find order nearest image centre (optical axis)
	bestDist, centreCorner = None, None
	centr, centc = None, None
	for r, row in enumerate(corners):
		for c, pos in enumerate(row):
			if pos[0] is None: continue
			dist = ((pos[0]-cent[0])**2. + (pos[1]-cent[1])**2.)**0.5
			#print pos, cent, dist
			if bestDist is None or dist < bestDist:
				bestDist = dist
				centr = r
				centc = c
				centreCorner = pos

	print "Centre corner", centr, centc, corners[centr][centc]

	#Find approximate size of squares near the centre
	offsets = [-1, 0], [1, 0], [0, -1], [0, 1]
	nearbyCornerDists = []
	for offset in offsets:
		r = centr + offset[0]
		c = centc + offset[1]
		pos = corners[r][c]
		if pos[0] is None: continue
		dist = ((pos[0]-centreCorner[0])**2. + (pos[1]-centreCorner[1])**2.)**0.5

		nearbyCornerDists.append(dist)

	if len(nearbyCornerDists) == 0:
		print "Define more points near image centre"
		exit(0)

	nearbyCornerDist = sum(nearbyCornerDists) / len(nearbyCornerDists)
	print "nearbyCornerDist", nearbyCornerDist

	#Calculate pattern offset
	patternShift = ((centreCorner[0] - cent[0]) / nearbyCornerDist, (centreCorner[1] - cent[1]) / nearbyCornerDist)
	print "patternShift", patternShift

	patternModel = PatternModel(180, 35.8)
	patternModel.patternShift = patternShift
	patternModel.centr = centr
	patternModel.centc = centc

	#LensFishEyeStereographicModel
	#LensFishEyeEquidistantModel
	#LensFishEquisolidAngleModel
	#LensOrthographicModel

	lens = LensFishEyeHybridModel(600)	

	#VisualisePoints(patternModel, corners, lens)
	result = opt.minimize(Eval, lens.GetParams(), args=[patternModel, lens])
	print result
	lens.SetParams(result.x)
	
	print "Error:", Eval(result.x, patternModel, lens)
	VisualisePoints(patternModel, corners, lens)

