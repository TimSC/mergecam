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

cdef RectilinearProj(double lat, double lon, double cLat, double cLon, double *xOut, double *yOut, int *validOut):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	cdef double cosc = sin(cLat) * sin(lat) + cos(cLat) * cos(lat) * cos(lon - cLon)
	if cosc < 0.:
		xOut[0] = 0
		yOut[0] = 0
		validOut[0] = 0
		return
	xOut[0] = (cos(lat) * sin(lon - cLon)) / cosc
	yOut[0] = (cos(cLat) * sin(lat) - sin(cLat) * cos(lat) * cos(lon - cLon)) / cosc
	validOut[0] = 1

def RectilinearProjSlow(double lat, double lon, double cLat, double cLon):
	cdef double x=0., y=0.
	cdef int valid = 0
	RectilinearProj(lat, lon, cLat, cLon, &x, &y, &valid)
	if valid:
		return x, y
	else:
		return None, None

cdef RectilinearUnProj(double x, double y, double cLat, double cLon, double *latOut, double *lonOut, int *validOut):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	cdef double rho = (x ** 2. + y ** 2.) ** 0.5
	cdef double c = atan(rho)
	cdef double sinc = sin(c)
	cdef double cosc = cos(c)
	latOut[0] = asin(cosc * sin(cLat) + y * sinc * cos(cLat) / rho)
	lonOut[0] = cLon + atan2(x * sinc, rho * cos(cLat) * cosc - y * sin(cLat) * sinc)
	validOut[0] = 1

def RectilinearUnProjSlow(double x, double y, double cLat, double cLon):
	cdef double lat=0., lon=0.
	cdef int valid = 0
	RectilinearUnProj(x, y, cLat, cLon, &lat, &lon, &valid)
	if valid:
		return lat, lon
	else:
		return None, None

class RectilinearCam(object):
	def __init__(self, hfov=49.0, vfov=35.4):
		self.imgW = 640
		self.imgH = 480
		self.cLat = 0.
		self.cLon = 0.
		self.rot = 0.

		self.hHRange = -1.
		self.hVRange = -1.
		self.SetFov(hfov, vfov)
		self.hsize = np.array((self.imgW/2, self.imgH/2))

	def SetFov(self, hfovIn, vfovIn):
		cdef double tempX = 0., tempY = 0.
		cdef int valid = 0
		self.hFov = math.radians(hfovIn)
		self.vFov = math.radians(vfovIn)
		cdef double hhFov = self.hFov / 2.
		cdef double hvFov = self.vFov / 2.

		RectilinearProj(0., hhFov, 0., 0., &tempX, &tempY, &valid)
		assert valid
		self.hHRange = tempX
		RectilinearProj(hvFov, 0., 0., 0., &tempX, &tempY, &valid)
		assert valid
		self.hVRange = tempY
		self.hRange = np.array((self.hHRange, self.hVRange))

	def UnProj(self, pts): #Image px to Lat, lon radians
		cdef double lat = 0., lon = 0.
		cdef int valid = 1

		pts = np.array(pts)
		centred = pts - self.hsize

		#Inverse rotate about origin
		mat = np.array([[cos(self.rot), -sin(self.rot)], [sin(self.rot), cos(self.rot)]])
		centred = np.dot(centred, mat)

		scaled = centred / self.hsize

		normImg = scaled * self.hRange
		out = []
		for pt in normImg:
			RectilinearUnProj(pt[0], pt[1], self.cLat, self.cLon, &lat, &lon, &valid)
			assert valid
			out.append((lat, lon))
		return out

	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		arr = np.array(ptsLatLon, dtype=np.float64)
		return self.ProjNumpy(arr)

	def ProjNumpy(self, np.ndarray[np.float64_t,ndim=2] ptsLatLon): #Lat, lon radians to image px

		cdef double x = 0., y = 0.
		cdef int valid = 1
		cdef np.ndarray[np.float64_t,ndim=2] imgPts = np.empty((ptsLatLon.shape[0],ptsLatLon.shape[1]), dtype=np.float64)
		cdef np.ndarray[np.int8_t,ndim=1] validLi = np.empty((ptsLatLon.shape[0],), dtype=np.int8)

		for ptNum in range(ptsLatLon.shape[0]):
			RectilinearProj(ptsLatLon[ptNum,0], ptsLatLon[ptNum,1], self.cLat, self.cLon, &x, &y, &valid)
			if valid:
				imgPts[ptNum,0] = x
				imgPts[ptNum,1] = y
				validLi[ptNum] = 1
			else:
				imgPts[ptNum,0] = 0.
				imgPts[ptNum,1] = 0.
				validLi[ptNum] = 0

		imgPts /= self.hRange
		imgPts *= self.hsize

		mat = np.array([[cos(self.rot), sin(self.rot)], [-sin(self.rot), cos(self.rot)]])
		imgPts = np.dot(imgPts, mat)

		#Move origin to corner
		imgPts += self.hsize

		for ind in np.where(validLi == False):
			imgPts[ind,0] = None
			imgPts[ind,1] = None

		return imgPts

def ThetaAngToLatLon(theta, ang):
	scalex = math.sin(ang)
	scaley = math.cos(ang)
	oppOverAdj = math.tan(theta) #Ratio of radius and object distance

	objXOverScreenCentDist = scalex * oppOverAdj
	objYOverScreenCentDist = scaley * oppOverAdj
	screenDistOnGroundPlane = (objXOverScreenCentDist ** 2. + 1.) ** 0.5

	lon = math.atan(objXOverScreenCentDist)
	lat = math.atan2(objYOverScreenCentDist, screenDistOnGroundPlane)
	return lat, lon

def LatLonToThetaAng(lat, lon):
	objXOverScreenCentDist = math.tan(lon)
	screenDistOnGroundPlane = (objXOverScreenCentDist ** 2. + 1.) ** 0.5

	objYOverScreenCentDist = math.tan(lat) * screenDistOnGroundPlane
	optAxisDist = (objXOverScreenCentDist ** 2. + objYOverScreenCentDist ** 2.) ** 0.5
	theta = math.atan(optAxisDist)

	if objYOverScreenCentDist != 0.:
		if objXOverScreenCentDist != 0.:
			ang = math.atan2(objXOverScreenCentDist, objYOverScreenCentDist)
		else:
			if objYOverScreenCentDist > 0.:
				ang = 0.
			else:
				ang = math.pi
	else:
		if objXOverScreenCentDist == 0.:
			ang = 0.
		else:
			if objXOverScreenCentDist > 0.:
				ang = math.pi / 2.
			else:
				ang = -math.pi / 2.
	return theta, ang

class EquirectangularCam(object):
	def __init__(self):
		self.imgW = 1024
		self.imgH = self.imgW / 2
		self.cLat = 0.
		self.cLon = 0.
		self.hFov = math.radians(360.0)
		self.vFov = math.radians(180.4)
		
	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		for pt in ptsLatLon:
			centred = (pt[1]-self.cLon, pt[0]-self.cLat)
			scaled = (centred[0] * 2. / self.hFov, centred[1] * 2. / self.vFov)
			scaled2 = (math.modf(scaled[0])[0], math.modf(scaled[1])[0])
			imgPos = ((scaled2[0] + 1.) * self.imgW * 0.5, (scaled2[1] + 1.) * self.imgH * 0.5)
			out.append(imgPos)
		return out

	def UnProj(self, ptsPix): #Image px to Lat, lon radians
		out = []
		for pt in ptsPix:
			centred = ((pt[0] * 2. / self.imgW) - 1., (pt[1] * 2. / self.imgH) - 1.)
			scaled = (centred[0] * self.hFov / 2., centred[1] * self.vFov / 2.)
			worldPos = (scaled[1] + self.cLon, scaled[0] + self.cLon)
			out.append(worldPos)
		return out

class FishEyeCamera(object):
	def __init__(self):
		self.f = 0.5
		self.imgW = 640
		self.imgH = 480
		self.k = 1.0
		self.cLat = 0.
		self.cLon = 0.
		
	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		for pt in ptsLatLon:
			#print "lat", pt[0], ", lon", pt[1]

			lat = pt[0]-self.cLat
			lon = pt[1]-self.cLon

			circles = lon / (2. * math.pi)
			if lon > 0.:
				lon = lon - math.floor(circles) * 2. * math.pi
			else:
				lon = lon - math.ceil(circles) * 2. * math.pi

			while lon > math.pi:
				lon -= math.pi * 2.
			while lon < -math.pi:
				lon += math.pi * 2.

			if abs(lon) > math.pi / 2.:
				out.append((None, None))
				continue

			#if lon2 < -math.pi:
			#	lon2 += math.pi * 2.
			#if lon2 > math.pi:
			#	lon2 -= math.pi * 2.

			#assert lon2 >= -math.pi * 2.
			#assert lon2 <= math.pi * 2.
			#if lon2 < -math.pi * 0.5 or lon2 > math.pi * 0.5: 
			#	#print "lon2", lon2, lon, self.cLon
			#	out.append((None, None))
			#	continue

			theta, ang = LatLonToThetaAng(lat, lon)

			#print "ang1=", ang, "theta1=",theta

			r = self.f * math.tan(self.k*theta)
			imx = 0.5 * self.imgW + math.sin(ang) * r * self.imgW
			imy = 0.5 * self.imgH + math.cos(ang) * r * self.imgW
			out.append((imx, imy))

		return out

	def UnProj(self, ptsPix): #Image px to Lat, lon radians
		out = []
		for pt in ptsPix:
			#print "pt", pt

			x2 = pt[0] - (0.5 * self.imgW)
			y2 = pt[1] - (0.5 * self.imgH)

			#print "x2", x2, ", y2", y2
			if y2 != 0.:
				ang = math.atan2(x2, y2)
				if x2 != 0.:
					#print "a"
					x3 = x2 / (math.sin(ang) * self.imgW)
					theta = math.atan2(x3, self.f) / self.k
				else:
					#print "b"
					if y2 > 0.:
						ang = 0.
					else:
						ang = math.pi
					y3 = y2 / self.imgW
					theta = math.atan2(abs(y3), self.f) / self.k

			else:
				if x2 != 0:
					#print "c"
					if x2 > 0:
						ang = math.pi / 2.
					else:
						ang = -math.pi / 2.
					x3 = x2 / self.imgW
					theta = math.atan2(abs(x3), self.f) / self.k
				else:
					#print "d"
					ang = 0.
					theta = 0.

			#print "ang2=", ang, "theta2=",theta

			lat, lon = ThetaAngToLatLon(theta, ang)

			outLat = lat+self.cLat
			outLon = lon+self.cLon
			out.append((outLat, outLon))

		return out

class GeniusWidecam(FishEyeCamera):
	def __init__(self):
		FishEyeCamera.__init__(self)
		self.f = 0.49389104
		self.k = 0.8260964

class FishEyePolyCorrectedCamera(object):
	def __init__(self):
		self.f = 0.5
		self.imgW = 640
		self.imgH = 480
		self.k = 1.0
		self.cLat = 0.
		self.cLon = 0.
		self.poly = InvertableFunc()
		self.polyCoeffs = [0., 1., 0., 0., 0.] #4th order
		self.poly.func = self.PolyEval

	def PolyEval(self, x):
		tot = 0.
		for i, c in enumerate(self.polyCoeffs):
			tot += (x ** i) * c
		return tot

	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		for pt in ptsLatLon:
			#print "lat", pt[0], ", lon", pt[1]

			lat = pt[0]-self.cLat
			lon = pt[1]-self.cLon

			circles = lon / (2. * math.pi)
			if lon > 0.:
				lon = lon - math.floor(circles) * 2. * math.pi
			else:
				lon = lon - math.ceil(circles) * 2. * math.pi

			while lon > math.pi:
				lon -= math.pi * 2.
			while lon < -math.pi:
				lon += math.pi * 2.

			if abs(lon) > math.pi / 2.:
				out.append((None, None))
				continue

			#if lon2 < -math.pi:
			#	lon2 += math.pi * 2.
			#if lon2 > math.pi:
			#	lon2 -= math.pi * 2.

			#assert lon2 >= -math.pi * 2.
			#assert lon2 <= math.pi * 2.
			#if lon2 < -math.pi * 0.5 or lon2 > math.pi * 0.5: 
			#	#print "lon2", lon2, lon, self.cLon
			#	out.append((None, None))
			#	continue

			theta, ang = LatLonToThetaAng(lat, lon)

			thetaCorrected = self.poly.InvFunc(theta)

			r = self.f * math.tan(self.k*thetaCorrected)
			imx = 0.5 * self.imgW + math.sin(ang) * r * self.imgW
			imy = 0.5 * self.imgH + math.cos(ang) * r * self.imgW
			out.append((imx, imy))

		return out

	def UnProj(self, ptsPix): #Image px to Lat, lon radians
		out = []
		for pt in ptsPix:
			#print "pt", pt

			x2 = pt[0] - (0.5 * self.imgW)
			y2 = pt[1] - (0.5 * self.imgH)

			#print "x2", x2, ", y2", y2
			if y2 != 0.:
				ang = math.atan2(x2, y2)
				if x2 != 0.:
					#print "a"
					x3 = x2 / (math.sin(ang) * self.imgW)
					theta = math.atan2(x3, self.f) / self.k
				else:
					#print "b"
					if y2 > 0.:
						ang = 0.
					else:
						ang = math.pi
					y3 = y2 / self.imgW
					theta = math.atan2(abs(y3), self.f) / self.k

			else:
				if x2 != 0:
					#print "c"
					if x2 > 0:
						ang = math.pi / 2.
					else:
						ang = -math.pi / 2.
					x3 = x2 / self.imgW
					theta = math.atan2(abs(x3), self.f) / self.k
				else:
					#print "d"
					ang = 0.
					theta = 0.

			#print "ang2=", ang, "theta2=",theta

			lat, lon = ThetaAngToLatLon(theta, ang)

			outLat = lat+self.cLat
			outLon = lon+self.cLon
			out.append((outLat, outLon))

		return out

class InvertableFunc(object):
	def __init__(self):
		self.x0 = 1.
		self.method = "Powell"
		self.func = lambda x: x ** 2

	def ErrEval(self, x, targety):
		err = abs(self.func(x)-targety)
		return err

	def InvFunc(self, y, verbose = 0):
		ret = optimize.minimize(self.ErrEval, self.x0, args=(y,), method=self.method)
		if verbose: print ret
		return ret.x



