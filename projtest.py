import math, proj
import numpy as np

if __name__ == "__main__":
	import matplotlib.pyplot as plt

	rectilinear = proj.Rectilinear()

	x, y = rectilinear.ProjSlow(0.1,0.2)
	print x, y
	print rectilinear.UnProjSlow(x, y)

	cLat = 0.
	cLon = 0.
	rectilinear.SetCentre(cLat, cLon)
	

	lonVals = np.arange(-1.5+cLon, 1.5+cLon, 0.1)
	latVals = np.arange(-1.+cLat, 1.+cLat, 0.1)
	for lon in lonVals:
		li = []
		for lat in latVals:
			li.append(rectilinear.ProjSlow(lat, lon))
		lia = np.array(li)
		plt.plot(lia[:,0], lia[:,1])

	for lat in latVals:
		li = []
		for lon in lonVals:
			li.append(rectilinear.ProjSlow(lat, lon))
		lia = np.array(li)
		#print li
		plt.plot(lia[:,0], lia[:,1])

	plt.show()

