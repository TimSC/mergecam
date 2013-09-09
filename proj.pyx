from math import sin, cos, atan2, pi, asin, atan
import math
import numpy as np

def RectilinearProj(lat, lon, cLat, cLon):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	cosc = sin(cLat) * sin(lat) + cos(cLat) * cos(lat) * cos(lon - cLon)
	if cosc < 0.:
		return None, None
	x = (cos(lat) * sin(lon - cLon)) / cosc
	y = (cos(cLat) * sin(lat) - sin(cLat) * cos(lat) * cos(lon - cLon)) / cosc
	return x, y

def RectilinearUnProj(x, y, cLat, cLon):
	#http://mathworld.wolfram.com/GnomonicProjection.html

	rho = (x ** 2. + y ** 2.) ** 0.5
	c = atan(rho)
	sinc = sin(c)
	cosc = cos(c)
	lat = asin(cosc * sin(cLat) + y * sinc * cos(cLat) / rho)
	lon = cLon + atan2(x * sinc, rho * cos(cLat) * cosc - y * sin(cLat) * sinc)
	return lat, lon

class RectilinearCam(object):
	def __init__(self):
		self.imgW = 640
		self.imgH = 480
		self.cLon = 0.
		self.cLat = 0.
		self.hFov = math.radians(49.0)
		self.vFov = math.radians(35.4)
		self.hwidth = RectilinearProj(0., self.hFov / 2.,self.cLat,self.cLon)[0]
		self.hheight = RectilinearProj(self.vFov / 2., 0.,self.cLat,self.cLon)[1]

	def UnProj(self, pts): #Image px to Lat, lon radians
		pts = np.array(pts)
		centred = pts - (self.imgW/2., self.imgH/2.)
		scaled = centred / (self.imgW/2., self.imgH/2.)

		normImg = scaled * (self.hwidth, self.hheight)
		polar = [RectilinearUnProj(pt[0],pt[1],self.cLat,self.cLon) for pt in normImg]
		return polar

	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		normImg = []
		valid = []
		for pt in ptsLatLon:
			pt2 = RectilinearProj(pt[0],pt[1],self.cLat,self.cLon)
			if pt2[0] is not None:
				normImg.append(pt2)
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

