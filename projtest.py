import math, proj
import numpy as np

if __name__ == "__main__":
	import matplotlib.pyplot as plt

	rectilinear = proj.Rectilinear()

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

