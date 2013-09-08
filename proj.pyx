# cython: profile=True
# cython: cdivision=True
# cython: boundscheck=False
# cython: wraparound=False

from math import pi
from libc.math cimport sin, cos, atan2, asin, atan
import math
import numpy as np
cimport numpy as np
import pickle

cdef RectilinearProj(float lat, float lon, float cLat, float cLon, float *xOut, float *yOut, int *validOut):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	cdef float cosc = sin(cLat) * sin(lat) + cos(cLat) * cos(lat) * cos(lon - cLon)

	if cosc < 0.:
		validOut[0] = 0
		xOut[0] = 0.
		yOut[0] = 0.
		return

	validOut[0] = 1
	xOut[0] = (cos(lat) * sin(lon - cLon)) / cosc
	yOut[0] = (cos(cLat) * sin(lat) - sin(cLat) * cos(lat) * cos(lon - cLon)) / cosc

cdef RectilinearUnProj(float x, float y, float cLat, float cLon, float *latOut, float *lonOut, int *validOut):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	cdef float rho = (x ** 2. + y ** 2.) ** 0.5
	cdef float c = atan(rho)
	cdef float sinc = sin(c)
	cdef float cosc = cos(c)
	validOut[0] = 1
	latOut[0] = asin(cosc * sin(cLat) + y * sinc * cos(cLat) / rho)
	lonOut[0] = cLon + atan2(x * sinc, rho * cos(cLat) * cosc - y * sin(cLat) * sinc)

def RectilinearProjSlow(float lat, float lon, float cLat, float cLon):
	cdef float x=0., y=0.
	cdef int valid = 0
	RectilinearProj(lat, lon, cLat, cLon, &x, &y, &valid)
	if valid:
		return x, y
	else:
		return None, None

def RectilinearUnProjSlow(float x, float y, float cLat, float cLon):
	cdef float lat=0., lon=0.
	cdef int valid = 0
	RectilinearUnProj(x, y, cLat, cLon, &lat, &lon, &valid)
	if valid:
		return lat, lon
	else:
		return None, None

class RectilinearCam(object):
	def __init__(self):
		self.imgW = 640
		self.imgH = 480
		self.cLat = 0.
		self.cLon = 0.

		self.hHRange = -1.
		self.hVRange = -1.
		self.SetFov(49.0, 35.4)

	def SetFov(self, hfovIn, vfovIn):
		cdef float tempX = 0., tempY = 0.
		cdef int valid = 0
		self.hFov = math.radians(hfovIn)
		self.vFov = math.radians(vfovIn)
		cdef float hhFov = self.hFov / 2.
		cdef float hvFov = self.vFov / 2.

		RectilinearProj(0., hhFov, 0., 0., &tempX, &tempY, &valid)
		assert valid
		self.hHRange = tempX
		RectilinearProj(hvFov, 0., 0., 0., &tempX, &tempY, &valid)
		assert valid
		self.hVRange = tempY

	def UnProj(self, pts): #Image px to Lat, lon radians
		cdef float lat = 0., lon = 0.
		cdef int valid = 1

		pts = np.array(pts)
		centred = pts - (self.imgW/2., self.imgH/2.)
		scaled = centred / (self.imgW/2., self.imgH/2.)

		normImg = scaled * (self.hHRange, self.hVRange)
		out = []
		for pt in normImg:
			RectilinearUnProj(pt[0], pt[1], self.cLat, self.cLon, &lat, &lon, &valid)
			assert valid
			out.append((lat, lon))
		return out

	def Proj(self, np.ndarray[np.float32_t,ndim=2] ptsLatLon): #Lat, lon radians to image px

		cdef float x = 0., y = 0.
		cdef int valid = 1
		cdef np.ndarray[np.float32_t,ndim=2] imgPts = np.empty((ptsLatLon.shape[0],ptsLatLon.shape[1]), dtype=np.float32)
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

		imgPts /= (self.hHRange, self.hVRange)
		imgPts *= (self.imgW/2., self.imgH/2.)
		imgPts += (self.imgW/2., self.imgH/2.)

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

