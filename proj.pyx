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

cdef class Rectilinear(object):
	cdef float cLon, cLat

	def __init__(self):
		self.cLon = 0.
		self.cLat = 0.

	cdef Proj(self, float lat, float lon, float *xOut, float *yOut, int *validOut):
		#http://mathworld.wolfram.com/GnomonicProjection.html

		cdef float cosc = sin(self.cLon) * sin(lat) + cos(self.cLon) * cos(lat) * cos(lon - self.cLon)
		if cosc < 0.:
			validOut[0] = 0
			xOut[0] = 0.
			yOut[0] = 0.

		validOut[0] = 1
		xOut[0] = (cos(lat) * sin(lon - self.cLon)) / cosc
		yOut[0] = (cos(self.cLon) * sin(lat) - sin(self.cLon) * cos(lat) * cos(lon - self.cLon)) / cosc

	def ProjSlow(self, float lat, float lon):
		cdef float x=0., y=0.
		cdef int valid = 0
		self.Proj(lat, lon, &x, &y, &valid)
		if valid:
			return x, y
		else:
			return None, None

	cdef UnProj(self, float x, float y, float *latOut, float *lonOut, int *validOut):
		#http://mathworld.wolfram.com/GnomonicProjection.html

		cdef float rho = (x ** 2. + y ** 2.) ** 0.5
		cdef float c = atan(rho)
		cdef float sinc = sin(c)
		cdef float cosc = cos(c)
		validOut[0] = 1
		latOut[0] = asin(cosc * sin(self.cLat) + y * sinc * cos(self.cLat) / rho)
		lonOut[0] = self.cLon + atan2(x * sinc, rho * cos(self.cLat) * cosc - y * sin(self.cLat) * sinc)

	def UnProjSlow(self, float x, float y):
		cdef float lat=0., lon=0.
		cdef int valid = 0
		self.UnProj(x, y, &lat, &lon, &valid)
		if valid:
			return lat, lon
		else:
			return None, None

	def __reduce__(self):
		state = {}
		state['lat'] = self.cLat
		state['lon'] = self.cLon
		return (RectilinearFactory, (pickle.dumps(state, protocol=-1),))

	def SetCentre(self, float lat, float lon):
		self.cLon = lon
		self.cLat = lat

	def GetCentre(self):
		return self.cLat, self.cLon

def RectilinearFactory(args):
	r = Rectilinear()
	stateDict = pickle.loads(args)
	r.SetCentre(stateDict['lat'], stateDict['lon'])
	return r

class RectilinearCam(object):
	def __init__(self):
		self.rectilinear = Rectilinear()
		self.imgW = 640
		self.imgH = 480
		self.hFov = math.radians(49.0)
		self.vFov = math.radians(35.4)
		self.rectStatic = Rectilinear()
		self.hwidth = -1.
		self.hheight = -1.
		temp, valid = -1., 0
		self.rectStatic.Proj(0., self.hFov / 2., self.hwidth, temp, valid)
		self.rectStatic.Proj(self.vFov / 2., 0., temp, self.hheight, valid)

	def UnProj(self, pts): #Image px to Lat, lon radians
		cdef float lat = 0., lon = 0.
		cdef int valid = 0

		pts = np.array(pts)
		centred = pts - (self.imgW/2., self.imgH/2.)
		scaled = centred / (self.imgW/2., self.imgH/2.)

		normImg = scaled * (self.hwidth, self.hheight)
		out = []
		for pt in normImg:
			self.rectilinear.UnProj(pt[0], pt[1], lat, lon, valid)
			assert valid
			out.append((lat, lon))
		return out

	def Proj(self, ptsLatLon): #Lat, lon radians to image px

		cdef float x = 0., y = 0.
		cdef int valid = 0

		normImg = []
		validLi = []
		for pt in ptsLatLon:
			self.rectilinear.Proj(pt[0], pt[1], x, y, valid)
			if valid:
				normImg.append((x, y))
				validLi.append(True)
			else:
				normImg.append((0.,0.))
				validLi.append(False)

		normImg = np.array(normImg)
		scaled = normImg / (self.hwidth, self.hheight)
		centred = scaled * (self.imgW/2., self.imgH/2.)
		imgPts = centred + (self.imgW/2., self.imgH/2.)

		for ind in np.where(np.array(validLi) == False):
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

