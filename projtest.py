import math, proj
import numpy as np

if __name__ == "__main__":
	import matplotlib.pyplot as plt

	x, y = proj.RectilinearProjSlow(0.1,0.2,0.,0.)
	print x, y
	print proj.RectilinearUnProjSlow(x, y, 0., 0.)

	cLat = 0.
	cLon = 0.

	lonVals = np.arange(-1.5+cLon, 1.5+cLon, 0.1)
	latVals = np.arange(-1.+cLat, 1.+cLat, 0.1)
	for lon in lonVals:
		li = []
		for lat in latVals:
			li.append(proj.RectilinearProjSlow(lat, lon, cLat, cLon))
		lia = np.array(li)
		plt.plot(lia[:,0], lia[:,1])

	for lat in latVals:
		li = []
		for lon in lonVals:
			li.append(proj.RectilinearProjSlow(lat, lon, cLat, cLon))
		lia = np.array(li)
		#print li
		plt.plot(lia[:,0], lia[:,1])

	plt.show()

