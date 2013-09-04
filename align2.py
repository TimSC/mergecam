
import pickle, rectilinear, os
import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as optimize

class CameraArrangement(object):
	def __init__(self, imgPairs):
		self.imgPairs = imgPairs
		self.addedPhotos = {}

	def OptimiseFit(self):

		if 0:
			plt.plot(ptsA[:,0], ptsA[:,1], '.')
			plt.plot(ptsB[:,0], ptsB[:,1], '.')
			plt.show()			

		if 0:
			proj1 = np.array(proj1)
			proj2 = np.array(proj2)
			plt.plot(proj1[:,0], proj1[:,1], '.')
			plt.plot(proj2[:,0], proj2[:,1], '.')
			plt.show()

		initialVals = []
		for i, phot in enumerate(self.addedPhotos):
			if i==0: continue
			camModel = self.addedPhotos[phot]
			initialVals.append(camModel.rectilinear.cLat)
			initialVals.append(camModel.rectilinear.cLon)

		print initialVals

		final = optimize.minimize(self.Eval, initialVals, method="Powell")
		print "score", final.x, final.fun

	def Eval(self, vals):

		dists = []
		for pair in self.imgPairs:
			fina1 = pair[1]
			fina2 = pair[2]
			if fina1 not in self.addedPhotos: continue
			if fina2 not in self.addedPhotos: continue

			fina1index = self.addedPhotos.keys().index(fina1)
			fina2index = self.addedPhotos.keys().index(fina2)

			#print fina1, fina2, fina1index, fina2index
			camModel1 = self.addedPhotos[fina1]
			if fina1index >= 1:
				camModel1.rectilinear.cLat = vals[(fina1index-1)*2]
				camModel1.rectilinear.cLon = vals[(fina1index-1)*2+1]
			camModel2 = self.addedPhotos[fina2]
			if fina2index >= 1:
				camModel2.rectilinear.cLat = vals[(fina2index-1)*2]
				camModel2.rectilinear.cLon = vals[(fina2index-1)*2+1]
			ptsA = np.array(pair[3])
			ptsB = np.array(pair[4])

			proj1 = camModel1.Proj(ptsA)
			proj2 = camModel2.Proj(ptsB)
			
			for pt1, pt2 in zip(proj1, proj2):
				malDist = abs(pt1[0]-pt2[0]) + abs(pt1[1]-pt2[1])
				dists.append(malDist)
		score = np.array(dists).mean()
		#print vals, score
		return score

if __name__=="__main__":
	imgPairs = pickle.load(open("imgpairs.dat", "rb"))

	l = "/home/tim/dev/glcamdata/house"
	poolPhotos = os.listdir(l)
	
	#Add two best photos
	imgPairs.sort()
	imgPairs.reverse()
	bestPair = imgPairs[0]
	print "Using initial photos", bestPair[7], bestPair[0]

	cameraArrangement = CameraArrangement(imgPairs)
	cameraArrangement.addedPhotos[bestPair[1]] = rectilinear.RectilinearCam()
	cameraArrangement.addedPhotos[bestPair[2]] = rectilinear.RectilinearCam()

	cameraArrangement.OptimiseFit()

	for pair in imgPairs:
		pairScore = pair[0]
		
		included1 = pair[1] in cameraArrangement.addedPhotos
		included2 = pair[2] in cameraArrangement.addedPhotos
		print pairScore, pair[1:3], included1, included2


