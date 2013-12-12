import math
import scipy.optimize as optimize
import numpy as np

class InvertableFunc(object):
	def __init__(self):
		self.x0 = 1.
		self.method = "Powell"
		self.func = lambda x: x ** 2
		self.xvals = None

	def ErrEval(self, x, targety):
		err = abs(self.func(x)-targety)
		return err

	def InvFuncByOptimize(self, y, verbose = 0):
		ret = optimize.minimize(self.ErrEval, self.x0, args=(y,), method=self.method)
		if verbose: print ret
		return ret.x

	def InvFuncByPiecewise(self, y, singleRoot = False):
		candidates = []
		for yv1, yv2, xv1, xv2 in zip(self.yvals[:-1], self.yvals[1:], self.xvals[:-1], self.xvals[1:]):
			if yv1 <= y and yv2 > y:
				rang = yv2 - yv1
				if rang > 0.:
					mix = (y - yv1) / rang
				else:
					mix = 0.
				x = mix * (xv2 - xv1) + xv1
				candidates.append(x)
				break

		if len(candidates)>0:
			return candidates
		else:
			return None

	def InvFunc(self, y):
		if self.xvals == None:
			self.EstimatePiecewiseInv(0., 2.)
		xcands = self.InvFuncByPiecewise(y, True)
		if xcands is not None:
			return xcands[0]
		return None #No root found

	def EstimatePiecewiseInv(self, minx, maxx, numPoints = 100):
		self.xvals = np.linspace(minx, maxx, numPoints)
		self.yvals = []
		for x in self.xvals:
			y = self.func(x)
			self.yvals.append(y)

		#import matplotlib.pyplot as plt
		#plt.plot(xvals, yvals)
		#plt.show()

		if 0:
			ytest = np.linspace(min(self.yvals), max(self.yvals), numPoints)
			xtest = []
			for y in ytest:
				xcands = self.InvFuncByPiecewise(y, True)
				if ycand is not None:
					xtest.append(xcands[0])
				else:
					xtest.append(None)

			#import matplotlib.pyplot as plt
			#plt.plot(self.yvals, self.xvals)
			#plt.plot(ytest, xtest)
			#plt.show()

	def __call__(self, x):
		return self.func(x)

# **************************************************************************

class FishEye(object):
	def __init__(self):
		self.imgW = 1280
		self.imgH = 1024
		self._a = 0.
		self._b = 0.
		self._c = 0.
		self.d = 0. / 1280.
		self.e = 0. / 1024.
		self.hfov = 118.75
		self.halfVfov = self.imgH * math.radians(self.hfov / 2.) / self.imgW
		self.cLat = 0.
		self.cLon = 0.
		self.rot = 0.

		self.correctionFunc = InvertableFunc()
		self.paramsChanged = True

	def UpdateCorrectionFunc(self):
		dval = 1 - (self._a + self._b + self._c)
		self.correctionFunc.func = lambda x: (x ** 4) * self._a + (x ** 3) * self._b + (x ** 2) * self._c + x * dval
		self.paramsChanged = False

	def SetCorrectionParams(self, ain, bin, cin):
		self._a = ain
		self._b = bin
		self._c = cin
		self.paramsChanged = True

	def PrepareForPickle(self):
		self.correctionFunc.func = None
		self.paramsChanged = True

	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		for pt in ptsLatLon:

			#Check that lon is in front of camera
			diff = (pt[1] - self.cLon + math.pi) % (2. * math.pi) - math.pi
			if diff < -math.pi * 0.5 or diff >= math.pi * 0.5:
				out.append((None, None))
				continue				

			#Convert lat lon to theta, ang
			screenX = math.tan(pt[1] - self.cLon)
			screenDistOnGnd = (screenX**2+1.)**0.5
			screenY = math.tan(pt[0] - self.cLat) * screenDistOnGnd

			ang = math.atan2(screenX, screenY)
			radius = (screenX ** 2. + screenY ** 2.) ** 0.5
			R = math.atan2(radius, math.tan(self.halfVfov)) / math.atan(1.)
			
			#print "a1", ang, R

			#Apply camera lens adjustment
			if self.paramsChanged:
				self.UpdateCorrectionFunc()
			Rcorrected = self.correctionFunc.InvFunc(R)

			#print "a2", Rcorrected
			if Rcorrected is None:
				out.append((None, None))
				continue

			#Calc centred image positions
			centImgX = Rcorrected * math.sin(ang) * (self.imgH / 2.)
			centImgY = Rcorrected * math.cos(ang) * (self.imgH / 2.)

			#print "a3", centImgX, centImgY

			#Calc rotation
			x1 = centImgX * math.cos(self.rot) - centImgY * math.sin(self.rot)
			y1 = centImgX * math.sin(self.rot) + centImgY * math.cos(self.rot)

			#Calc final position
			x2 = x1 + (self.imgW / 2.)
			y2 = y1 + (self.imgH / 2.)
			x = x2 - self.d * self.imgW
			y = y2 - self.e * self.imgH

			if x < 0. or x >= self.imgW:
				out.append((None, None))
				continue
			if y < 0. or y >= self.imgH:
				out.append((None, None))
				continue

			out.append((x, y))

		return out

	def UnProj(self, ptsPix): #Image px to Lat, lon radians

		out = [] 
		for pt in ptsPix:
			#Centre image
			centImgX = pt[0] - (self.imgW / 2.) + self.d * self.imgW
			centImgY = pt[1] - (self.imgH / 2.) + self.e * self.imgH

			#print "b3", centImgX, centImgY

			#Apply rotation
			rotx = centImgX * math.cos(-self.rot) - centImgY * math.sin(-self.rot)
			roty = centImgX * math.sin(-self.rot) + centImgY * math.cos(-self.rot)			

			#Normalise positions
			centImgX2 = rotx / (self.imgH / 2.)
			centImgY2 = roty / (self.imgH / 2.)

			#Calculate radius and angle
			R = (centImgX2 ** 2. + centImgY2 ** 2.) ** 0.5
			ang = math.atan2(centImgX2, centImgY2)
			
			#print "b2", R

			#Apply lens correction function
			if self.paramsChanged:
				self.UpdateCorrectionFunc()
			Rcorrected = self.correctionFunc(R)

			#print "b1", ang, Rcorrected

			#Calculate x and y in screen plane
			radius = math.tan(Rcorrected * math.atan(1.)) * math.tan(self.halfVfov)
			screenX = radius * math.sin(ang)
			screenY = radius * math.cos(ang)
			screenDistOnGnd = (screenX**2+1.)**0.5
			
			#Convert to lat and lon
			lon = math.atan(screenX) + self.cLon
			lat = math.atan2(screenY, screenDistOnGnd) + self.cLat
			out.append((lat, lon))

		return out



if __name__ == "__main__":
	
	x, y = 226.2789025152, 108.4201414704


	cam = FishEye()
	latLons = cam.UnProj([[x, y]])

	print [map(math.degrees, pt) for pt in latLons]

	pos2 = cam.Proj(latLons)

	print pos2

