
import csv, math
import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize as opt

#Results on genius widecam
#3rd order poly	    14.3005542503
#Hybrid	            15.5126199515
#Stereographic      22.5737763356
#EquidistantModel   25.2579427817
#EquisolidAngle     33.0249503865
#OrthographicModel  44.681095153
#Rectilinear        68.8396171272

def MapToFloat(nums):
	out = []
	for v in nums:
		try:
			out.append(float(v))
		except ValueError:
			out.append(None)
	return out

def ReadCoord(fina):
	csvdata = csv.reader(fina, delimiter='\t')
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
		self.rx = 0.
		self.ry = 0.
		self.rz = 0.

	def GetPoint(self, row, col):
		rowOff = row - self.centr
		colOff = col - self.centc

		x = rowOff + self.squareSize * self.patternShift[0] + colOff * self.squareSize
		y = rowOff + self.squareSize * self.patternShift[1] + rowOff * self.squareSize

		vec = np.array([x, y, 1.])
		
		Rx = np.array([[1.,0.,0.],
			[0., math.cos(self.rx),-math.sin(self.rx)], 
			[0., math.sin(self.rx), math.cos(self.rx)]])

		Ry = np.array([[math.cos(self.ry),0.,math.sin(self.ry)],
			[0., 1., 0.], 
			[math.sin(self.ry), 0., math.cos(self.ry)]])	

		Rz = np.array([[math.cos(self.rz),-math.sin(self.rz),0.],
			[math.sin(self.rz), math.cos(self.rz), 0.], 
			[0., 0., 1.]])	

		vec2 = np.dot(Rx, vec)
		vec3 = np.dot(Ry, vec2)
		vec4 = np.dot(Rz, vec3)

		#print vec4

		optAxisDist = (vec4[0]**2. + vec4[1]**2.)**0.5

		theta = math.atan2(optAxisDist, self.screenDist)
		ang = math.atan2(vec4[0], vec4[1])
		return theta, ang

	def GetParams(self):
		return self.rx, self.ry, self.rz

	def SetParams(self, p):
		self.rx = p[0]
		self.ry = p[1]
		self.rz = p[2]

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

	def GetParams(self):
		return [self.f]

	def SetParams(self, p):
		self.f = p[0]

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

class LensPolynomialModel(object):
	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h
		self.c = [1., 0., 0.]

	def Proj(self, theta, ang):
		tot = 0.
		for i, coeff in enumerate(self.c):
			tot += coeff * (theta ** (i+1))
		r = self.f * tot
		imx = 0.5 * self.w + math.sin(ang) * r
		imy = 0.5 * self.h + math.cos(ang) * r
		return imx, imy

	def GetParams(self):
		out = [self.f]
		out.extend(self.c)
		return out

	def SetParams(self, p):
		self.f = p[0]
		self.c = p[1:]

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

	def GetParams(self):
		return [self.f]

	def SetParams(self, p):
		self.f = p[0]


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

	def GetParams(self):
		return [self.f]

	def SetParams(self, p):
		self.f = p[0]

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

	def GetParams(self):
		return [self.f]

	def SetParams(self, p):
		self.f = p[0]

class LensRectilinearModel(object):

	def __init__(self, f=10., w=1280, h=1024):
		self.f = f
		self.w = w
		self.h = h

	def Proj(self, theta, ang):
		cLat = 0.
		cLon = 0.
		
		x = math.cos(ang)
		y = math.sin(ang)
		oppOverAdj = math.tan(theta)

		lat = math.atan(y * oppOverAdj)
		lon = math.atan(x * oppOverAdj)

		cosc = math.sin(cLat) * math.sin(lat) + math.cos(cLat) * math.cos(lat) * math.cos(lon - cLon)
		if cosc < 0.:
			xOut[0] = 0
			yOut[0] = 0
			validOut[0] = 0
			return
		xo = (math.cos(lat) * math.sin(lon - cLon)) / cosc
		yo = (math.cos(cLat) * math.sin(lat) - math.sin(cLat) * math.cos(lat) * math.cos(lon - cLon)) / cosc

		return xo * self.f + self.w / 2., yo * self.f + self.h / 2.

	def GetParams(self):
		return [self.f]

	def SetParams(self, p):
		self.f = p[0]








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

def Eval(params, patternModel, lens, numLensParam, numPatternParam):
	print params
	errs = []
	lens.SetParams(params[:numLensParam])
	patternModel.SetParams(params[numLensParam:])

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
	#LensPolynomialModel
	#LensRectilinearModel

	lens = LensRectilinearModel(600)

	#VisualisePoints(patternModel, corners, lens)
	numLensParam = len(lens.GetParams())
	numPatternParam = len(patternModel.GetParams())
	x0 = list(lens.GetParams())
	x0.extend(patternModel.GetParams())

	result = opt.minimize(Eval, x0, args=[patternModel, lens, numLensParam, numPatternParam], tol=1e-3)
	print result
	lens.SetParams(result.x[:numLensParam])
	patternModel.SetParams(result.x[numLensParam:])
	
	print "Error:", Eval(result.x, patternModel, lens, numLensParam, numPatternParam)
	print "Lens params:", result.x[:numLensParam]
	print "Pattern params:", result.x[numLensParam:]

	VisualisePoints(patternModel, corners, lens)

