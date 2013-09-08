from math import sin, cos, atan2, pi, asin, atan
import math
import numpy as np

class Rectilinear(object):
	def __init__(self):
		self.cLon = 0.
		self.cLat = 0.

	def Proj(self, lat, lon):
		#http://mathworld.wolfram.com/GnomonicProjection.html

		cosc = sin(self.cLat) * sin(lat) + cos(self.cLat) * cos(lat) * cos(lon - self.cLon)
		x = (cos(lat) * sin(lon - self.cLon)) / cosc
		y = (cos(self.cLat) * sin(lat) - sin(self.cLat) * cos(lat) * cos(lon - self.cLon)) / cosc
		return x, y

	def UnProj(self, x, y):
		##http://mathworld.wolfram.com/GnomonicProjection.html

		rho = (x ** 2. + y ** 2.) ** 0.5
		c = atan(rho)
		sinc = sin(c)
		cosc = cos(c)
		lat = asin(cosc * sin(self.cLat) + y * sinc * cos(self.cLat) / rho)
		lon = self.cLon + atan2(x * sinc, rho * cos(self.cLat) * cosc - y * sin(self.cLat) * sinc)
		return lat, lon

class RectilinearCam(object):
	def __init__(self):
		self.rectilinear = Rectilinear()
		self.imgW = 640
		self.imgH = 480
		self.hFov = math.radians(49.0)
		self.vFov = math.radians(35.4)

	def UnProj(self, pts): #Image px to Lat, lon radians
		pts = np.array(pts)
		centred = pts - (self.imgW/2., self.imgH/2.)
		scaled = centred / (self.imgW/2., self.imgH/2.)
		hwidth = self.rectilinear.Proj(0., self.hFov / 2.)[0]
		hheight = self.rectilinear.Proj(self.vFov / 2., 0.)[1]
		normImg = scaled * (hwidth, hheight)
		polar = [self.rectilinear.UnProj(*pt) for pt in normImg]
		return polar

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
			centred = (pt[0]-self.cLon, pt[1]-self.cLat)
			scaled = (centred[0] * 2. / self.hFov, centred[1] * 2. / self.vFov)
			imgPos = ((scaled[0] + 1.) * self.imgW * 0.5, (scaled[1] + 1.) * self.imgH * 0.5)
			out.append(imgPos)
		return out

if __name__ == "__main__":
	import matplotlib.pyplot as plt

	rectilinear = Rectilinear()

	x, y = rectilinear.Proj(0.1,0.2)
	print x, y
	print rectilinear.UnProj(x, y)

	rectilinear.cLat = 0.
	rectilinear.cLon = 0.

	lonVals = np.arange(-1.5+rectilinear.cLon, 1.5+rectilinear.cLon, 0.1)
	latVals = np.arange(-1.+rectilinear.cLat, 1.+rectilinear.cLat, 0.1)
	for lon in lonVals:
		li = []
		for lat in latVals:
			li.append(rectilinear.Proj(lat, lon))
		lia = np.array(li)
		plt.plot(lia[:,0], lia[:,1])

	for lat in latVals:
		li = []
		for lon in lonVals:
			li.append(rectilinear.Proj(lat, lon))
		lia = np.array(li)
		#print li
		plt.plot(lia[:,0], lia[:,1])

	plt.show()

