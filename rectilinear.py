from math import sin, cos, atan2, pi
import numpy as np

class Rectilinear(object):
	def __init__(self):
		self.cLon = 0.5
		self.cLat = 0.5

	def Proj(self, lat, lon):
		#http://mathworld.wolfram.com/GnomonicProjection.html

		cosc = sin(self.cLat) * sin(lat) + cos(self.cLat) * cos(lat) * cos(lon - self.cLon)
		x = (cos(lat) * sin(lon - self.cLon)) / cosc
		y = (cos(self.cLat) * sin(lat) - sin(self.cLat) * cos(lat) * cos(lon - self.cLon)) / cosc

		return x, y

if __name__ == "__main__":
	import matplotlib.pyplot as plt

	rectilinear = Rectilinear()

	lonVals = np.arange(-1.5, 1.5, 0.1)
	latVals = np.arange(-1., 1., 0.1)
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

