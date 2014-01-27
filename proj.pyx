# cython: profile=True
# cython: cdivision=True
# cython: boundscheck=False
# cython: wraparound=False

from math import pi
from libc.math cimport sin, cos, atan2, asin, atan
import math
import numpy as np
cimport numpy as np
import scipy.optimize as optimize

class EquirectangularCam(object):
	def __init__(self):
		self.imgW = 1024
		self.imgH = self.imgW / 2
		self.cLat = 0.
		self.cLon = 0.
		self.hFov = math.radians(360.0)
		self.vFov = math.radians(180.0)
		self.limitRange = 0
		
	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		#print self.hFov, self.vFov, self.imgW, self.imgH

		#lats = [pt[0] for pt in ptsLatLon]
		#lons = [pt[1] for pt in ptsLatLon]
		#print "lats:", min(lats), max(lats), "lons:", min(lons), max(lons)

		out = []
		for pt in ptsLatLon:
			centred = (pt[1]-self.cLon, pt[0]-self.cLat)
			scaled = (centred[0] * 2. / self.hFov, centred[1] * 2. / self.vFov)
			if self.limitRange:
				scaled2 = (math.modf(scaled[0])[0], math.modf(scaled[1])[0])
				imgPos = ((scaled2[0] + 1.) * self.imgW * 0.5, (scaled2[1] + 1.) * self.imgH * 0.5)
			else:
				imgPos = ((scaled[0] + 1.) * self.imgW * 0.5, (scaled[1] + 1.) * self.imgH * 0.5)
			out.append(imgPos)

		#xs = [pt[0] for pt in out]
		#ys = [pt[1] for pt in out]
		#print "x:", min(xs), max(xs), "y:", min(ys), max(ys)

		return out

	def MultiProj(self, ptsLatLon): #Lat, lon radians to image px
		#print self.hFov, self.vFov, self.imgW, self.imgH

		#lats = [pt[0] for pt in ptsLatLon]
		#lons = [pt[1] for pt in ptsLatLon]
		#print "lats:", min(lats), max(lats), "lons:", min(lons), max(lons)

		out = []
		for pt in ptsLatLon:
			centred = (pt[1]-self.cLon, pt[0]-self.cLat)
			scaled = (centred[0] * 2. / self.hFov, centred[1] * 2. / self.vFov) #Range from -1 to 1
			print scaled
			if self.limitRange:
				scaled = (math.modf(scaled[0])[0], math.modf(scaled[1])[0])
			scaled2 = (scaled[0] + 1. * 0.5, scaled[1] + 1. * 0.5) #Range from 0 to 1

			imgPos = (scaled2[0] * self.imgW, scaled2[1] * self.imgH)

			#Check if wrapping around one width is still in the image
			rpos = None
			lpos = None
			scaled2r = (scaled2[0] + math.radians(360.) / self.hFov, scaled2[1])
			if scaled2r[0] >= -0.5 and scaled2r[0] < 1.5:
				rpos = (scaled2r[0] * self.imgW, scaled2r[1] * self.imgH)
			scaled2l = (scaled2[0] - math.radians(360.) / self.hFov, scaled2[1])
			if scaled2l[0] >= -0.5 and scaled2l[0] < 1.5:
				lpos = (scaled2l[0] * self.imgW, scaled2l[1] * self.imgH)

			out.append([imgPos, lpos, rpos])

		#xs = [pt[0] for pt in out]
		#ys = [pt[1] for pt in out]
		#print "x:", min(xs), max(xs), "y:", min(ys), max(ys)

		return out


	def UnProj(self, ptsPix): #Image px to Lat, lon radians
		out = []
		for pt in ptsPix:
			centred = ((pt[0] * 2. / self.imgW) - 1., (pt[1] * 2. / self.imgH) - 1.)
			scaled = (centred[0] * self.hFov / 2., centred[1] * self.vFov / 2.)
			worldPos = (scaled[1] + self.cLon, scaled[0] + self.cLon)
			out.append(worldPos)
		return out

	def __repr__(self):
		return "EquirectangularCam"+str(self.GetParams())

	def GetParams(self):
		return {'imgW': self.imgW, 'imgH': self.imgH, 'cLat': self.cLat, 'cLon': self.cLon, 'hFov': self.hFov, 'vFov': self.vFov, 
			'limitRange': self.limitRange}

# ************************************************************************************

class InvertableFunc(object):
	def __init__(self):
		self.x0 = 1.
		self.method = "Powell"
		self.func = lambda x: x ** 2
		self.xvals = None
		self.yvals = None

	def ErrEval(self, x, targety):
		err = abs(self.func(x)-targety)
		return err

	def InvFuncByOptimize(self, y, verbose = 0):
		ret = optimize.minimize(self.ErrEval, self.x0, args=(y,), method=self.method)
		if verbose: print ret
		return ret.x

	def InvFuncByPiecewise(self, y, singleRoot = False):
		candidates = []
		xlen = len(self.yvals)
		ylen = len(self.yvals)
		for yv1, yv2, xv1, xv2 in zip(self.yvals[:ylen-1], self.yvals[1:], self.xvals[:xlen-1], self.xvals[1:]):
			if min([yv1, yv2]) <= y and max([yv1, yv2]) > y:
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
		#print "yvals", min(self.yvals), max(self.yvals), len(self.yvals)
		#print "xvals", min(self.xvals), max(self.xvals), len(self.xvals)
		#if y >= self.yvals[0] or y < self.yvals[-1]:
		#	raise Exception("Error in inverse func at " +str(y))
		#print self.xvals
		#print self.yvals
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

class BaseCam(object):
	def __init__(self):
		self.imgW = 1280
		self.imgH = 1024
		self._a = 0.
		self._b = 0.
		self._c = 0.
		self.d = 0. / 1280.
		self.e = 0. / 1024.
		self.hfov = 118.75
		self.cLat = 0.
		self.cLon = 0.
		self.rot = 0.

		self.correctionFunc = InvertableFunc()
		self.paramsChanged = True

	def __repr__(self):
		return "BaseCam"+str(self.GetParams())

	def UpdateCorrectionFunc(self):
		dval = 1 - (self._a + self._b + self._c)
		self.correctionFunc.func = lambda x: (x ** 4) * self._a + (x ** 3) * self._b + (x ** 2) * self._c + x * dval
		self.paramsChanged = False

	def SetCorrectionParams(self, ain, bin, cin):
		if ain is not None: self._a = ain
		if bin is not None: self._b = bin
		if cin is not None: self._c = cin
		self.paramsChanged = True

	def PrepareForPickle(self):
		self.correctionFunc.func = None
		self.paramsChanged = True

	def CoreProjFunc(self, theta):
		return theta

	def CoreProjFuncInv(self, R):
		return R

	def GetParams(self):
		return {'hfov': self.hfov, 'a': self._a, 'b': self._b, 'c': self._c, 'd': self.d, 'e': self.e, 
			'cLat': self.cLat, 'cLon': self.cLon, 'rot': self.rot, 'imgW': self.imgW, 'imgH': self.imgH}

	def SetParams(self, params):
		if 'a' in params: self._a = params['a']
		if 'b' in params: self._b = params['b']
		if 'c' in params: self._c = params['c']
		if 'd' in params: self.d = params['d']
		if 'e' in params: self.e = params['e']
		if 'hfov' in params: self.hfov = params['hfov']
		if 'imgW' in params: self.imgW = params['imgW']
		if 'imgH' in params: self.imgH = params['imgH']

		self.paramsChanged = True
	
	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		halfVfov = self.imgH * math.radians(self.hfov / 2.) / self.imgW

		for pt in ptsLatLon:

			#Check that lon is in front of camera
			londiff = (pt[1] - self.cLon + math.pi) % (2. * math.pi) - math.pi
			if londiff < -math.pi * 0.5 or londiff >= math.pi * 0.5:
				out.append((None, None))
				continue
			latdiff = (pt[0] - self.cLat + math.pi * 0.5) % (math.pi) - (0.5 * math.pi)

			#Convert lat lon to theta, ang
			screenX = math.tan(londiff)
			screenDistOnGnd = (screenX**2+1.)**0.5
			screenY = math.tan(latdiff) * screenDistOnGnd

			ang = math.atan2(screenX, screenY)
			radius = (screenX ** 2. + screenY ** 2.) ** 0.5
			theta = math.atan2(radius, math.tan(halfVfov)) / math.atan(1.)
			R = self.CoreProjFunc(theta)

			#print "a1", ang, R

			#Apply camera lens adjustment
			if self.paramsChanged:
				self.UpdateCorrectionFunc()
			try:
				Rcorrected = self.correctionFunc.InvFunc(R)
			except Exception as err:
				print err
				out.append((None, None))
				continue

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
		halfVfov = self.imgH * math.radians(self.hfov / 2.) / self.imgW

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

			theta = self.CoreProjFuncInv(Rcorrected)

			#Calculate x and y in screen plane
			radius = math.tan(theta * math.atan(1.)) * math.tan(halfVfov)
			screenX = radius * math.sin(ang)
			screenY = radius * math.cos(ang)
			screenDistOnGnd = (screenX**2+1.)**0.5
			
			#Convert to lat and lon
			lon = math.atan(screenX) + self.cLon
			lat = math.atan2(screenY, screenDistOnGnd) + self.cLat
			out.append((lat, lon))

		return out

class FishEye(BaseCam):
	def __init__(self):
		BaseCam.__init__(self)
	
	def CoreProjFunc(self, theta):
		return theta

	def CoreProjFuncInv(self, R):
		return R

class Rectilinear(BaseCam):
	def __init__(self):
		BaseCam.__init__(self)
	
	def CoreProjFunc(self, theta):
		return math.tan(theta)

	def CoreProjFuncInv(self, R):
		return math.atan(R)

