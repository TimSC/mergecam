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

cdef RectilinearUnProj(double x, double y, double cLat, double cLon, double *latOut, double *lonOut, int *validOut):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	cdef double rho = (x ** 2. + y ** 2.) ** 0.5
	cdef double c = atan(rho)
	cdef double sinc = sin(c)
	cdef double cosc = cos(c)
	latOut[0] = asin(cosc * sin(cLat) + y * sinc * cos(cLat) / rho)
	lonOut[0] = cLon + atan2(x * sinc, rho * cos(cLat) * cosc - y * sin(cLat) * sinc)
	validOut[0] = 1

class RectilinearCam(object):
	def __init__(self):
		self.imgW = 640
		self.imgH = 480
		self.cLon = 0.
		self.cLat = 0.
		self.hFov = math.radians(49.0)
		self.vFov = math.radians(35.4)

		cdef double latTmp = 0., lonTmp = 0.
		cdef int valid = 0
		RectilinearProj(0., self.hFov / 2.,self.cLat,self.cLon,&latTmp,&lonTmp,&valid)
		self.hwidth = latTmp
		RectilinearProj(self.vFov / 2., 0.,self.cLat,self.cLon,&latTmp,&lonTmp,&valid)
		self.hheight = lonTmp

	def UnProj(self, pts): #Image px to Lat, lon radians
		cdef double latTmp = 0., lonTmp = 0.
		cdef int validTmp = 0

		pts = np.array(pts)
		centred = pts - (self.imgW/2., self.imgH/2.)
		scaled = centred / (self.imgW/2., self.imgH/2.)

		normImg = scaled * (self.hwidth, self.hheight)
		polar = []
		for pt in normImg:
			RectilinearUnProj(pt[0],pt[1],self.cLat,self.cLon,&latTmp,&lonTmp,&validTmp)
			polar.append((latTmp,lonTmp))
		return polar

	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		cdef double xTmp = 0., yTmp = 0.
		cdef int validTmp = 0

		normImg = []
		valid = []
		for pt in ptsLatLon:

			RectilinearProj(pt[0],pt[1],self.cLat,self.cLon,&xTmp,&yTmp,&validTmp)

			if validTmp:
				normImg.append((xTmp, yTmp))
				valid.append(True)
			else:
				normImg.append((0.,0.))
				valid.append(False)

		normImg = np.array(normImg)
		scaled = normImg / (self.hwidth, self.hheight)
		centred = scaled * (self.imgW/2., self.imgH/2.)
		imgPts = centred + (self.imgW/2., self.imgH/2.)

		for ind in np.where(np.array(valid) == False):
			imgPts[ind] = (None, None)

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

