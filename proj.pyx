# cython: profile=True
# cython: cdivision=True
# cython: boundscheck=False
# cython: wraparound=False

from math import pi
from libc.math cimport sin, cos, atan2, asin, atan
import math
import numpy as np
cimport numpy as np

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

class GeniusWidecam(object):
	def __init__(self):
		self.f = 0.49389104
		self.w = 640
		self.h = 480
		self.k = 0.8260964
		self.cLat = 0.
		self.cLon = 0.
		
	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		for pt in ptsLatLon:

			lat = pt[0]+self.cLat
			lon = pt[1]+self.cLon

			xdist = math.tan(lon)
			ydist = math.tan(lat)
			dist = (xdist ** 2. + ydist ** 2.) ** 0.5

			ang = math.atan2(xdist, ydist)
			theta = math.atan(dist)

			r = self.f * math.tan(self.k*theta)
			imx = 0.5 * self.w + math.sin(ang) * r * self.w
			imy = 0.5 * self.h + math.cos(ang) * r * self.w
			out.append((imx, imy))

		return out

	def UnProj(self, ptsPix): #Image px to Lat, lon radians
		out = []
		for pt in ptsPix:

			x2 = pt[0] - (0.5 * self.w)
			y2 = pt[1] - (0.5 * self.h)
			ang = math.atan2(x2, y2)
			x3 = x2 / (math.sin(ang) * self.w)
			theta = math.atan2(x3, self.f) / self.k

			x = math.sin(ang)
			y = math.cos(ang)
			oppOverAdj = math.tan(theta)

			lat = math.atan(y * oppOverAdj)
			lon = math.atan(x * oppOverAdj)
			out.append((lat-self.cLat, lon-self.cLon))

		return out



