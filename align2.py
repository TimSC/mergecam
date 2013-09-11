
import pickle, proj, os, math, visualise
import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as optimize

class CameraArrangement(object):
	def __init__(self, imgPairs):
		self.imgPairs = imgPairs
		self.addedPhotos = {}

	def OptimiseFit(self, photToOpt = None, optRotation=False):

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

		if photToOpt is None:
			photToOpt = self.addedPhotos

		initialVals = []
		initialValKey = {}
		for i, phot in enumerate(self.addedPhotos):
			if photToOpt is not None and phot not in photToOpt: continue
			camModel = self.addedPhotos[phot]
			initialValKey[phot] = {}
			initialValKey[phot]["lat"] = len(initialVals)
			initialVals.append(camModel.cLat)
			initialValKey[phot]["lon"] = len(initialVals)
			initialVals.append(camModel.cLon)
			if optRotation:
				initialValKey[phot]["rot"] = len(initialVals)
				initialVals.append(camModel.rot)

		print initialVals

		if 0:
			final = optimize.minimize(self.Eval, initialVals, (0, initialValKey, photToOpt), method="Powell")
			print "score", final.x, final.fun
		if 1:
			final = optimize.leastsq(self.Eval, initialVals, (1, initialValKey, photToOpt), xtol=1e-4)
			print "score", final
			finalVals = final[0]

		#Set values
		for phot in initialValKey:
			params = initialValKey[phot]
			self.addedPhotos[phot].cLat = finalVals[params["lat"]]
			self.addedPhotos[phot].cLon = finalVals[params["lon"]]
			if "rot" in params:
				self.addedPhotos[phot].rot = finalVals[params["rot"]]

	def Eval(self, vals, separateTerms, initialValKey, photToOpt):

		dists = []
		countPairs = 0

		for pair in self.imgPairs:
			weight = pair[0]
			fina1 = pair[1]
			fina2 = pair[2]
			if fina1 not in self.addedPhotos: continue
			if fina2 not in self.addedPhotos: continue
			if fina1 not in photToOpt and fina2 not in photToOpt: continue
			countPairs += 1

			#print fina1, fina2, fina1index, fina2index
			camModel1 = self.addedPhotos[fina1]
			if fina1 in initialValKey:
				camModel1.cLat = vals[initialValKey[fina1]["lat"]]
				camModel1.cLon = vals[initialValKey[fina1]["lon"]]
				if "rot" in initialValKey[fina1]:
					camModel1.rot = vals[initialValKey[fina1]["rot"]]

			camModel2 = self.addedPhotos[fina2]
			if fina2 in initialValKey:
				camModel2.cLat = vals[initialValKey[fina2]["lat"]]
				camModel2.cLon = vals[initialValKey[fina2]["lon"]]
				if "rot" in initialValKey[fina2]:
					camModel2.rot = vals[initialValKey[fina2]["rot"]]

			ptsA = np.array(pair[3])
			ptsB = np.array(pair[4])
			
			#Use only a subset of points
			ptsA = ptsA[:,:]
			ptsB = ptsB[:,:]

			proj1 = camModel1.UnProj(ptsA)
			proj2 = camModel2.UnProj(ptsB)
			
			distsX = []
			distsY = []
			for pt1, pt2 in zip(proj1, proj2):
				malDist1 = abs(pt1[0]-pt2[0])#Lat 
				malDist2 = abs(pt1[1]-pt2[1])#Lon
				while malDist2 > math.pi: #Limit difference to -pi to +pi range
					malDist2 -= 2. * math.pi

				distsX.append(malDist1 * weight)
				distsY.append(malDist2 * weight)

			dists.append(np.array(distsX).mean())
			dists.append(np.array(distsY).mean())

		#print vals, score
		#print countPairs

		if separateTerms:
			return np.power(dists, 1.)
		score = np.array(dists).mean() ** 1.
		return score

def SelectPhotoToAdd(imgPairs, cameraArrangement):
	bestScore = None
	bestPair = None
	bestNewInd = None
	for pair in imgPairs:
		pairScore = pair[0]
		
		included1 = pair[1] in cameraArrangement.addedPhotos
		included2 = pair[2] in cameraArrangement.addedPhotos
		if included1 + included2 != 1: continue
		#print pairScore, pair[1:3], included1, included2
		if bestScore is None or pairScore > bestScore:
			bestScore = pairScore
			bestPair = pair
			bestNewInd = included1

	return bestPair, bestNewInd

def GetStrongestLinkForPhotoId(imgPairs, photoId):

	bestScore = None
	bestPair = None
	for pair in imgPairs:
		if photoId != pair[1] and photoId != pair[2]: continue
		if bestScore is None or pair[0] > bestScore:
			bestScore = pair[0]
			bestPair = pair
	return bestPair, bestScore

if __name__=="__main__":
	imgPairs = pickle.load(open("imgpairs.dat", "rb"))

	poolPath = "/home/tim/dev/glcamdata/house"
	poolPhotos = os.listdir(poolPath)

	log = open("log.txt", "wt")
	
	#Select valid pairings based on threshold
	filteredImgPairs = []
	for pair in imgPairs:
		if pair[0] > 0.1:
			filteredImgPairs.append(pair)

	#Check all photos are referenced in filtered set
	refPhotos = set()
	for pair in filteredImgPairs:
		refPhotos.add(pair[1])
		refPhotos.add(pair[2])

	missingPhotos = set()
	for photoId in poolPhotos:
		if photoId in refPhotos: continue
		missingPhotos.add(photoId)

	if 0:
		#For photos with no links, add their best link
		for photoId in missingPhotos:
			pair, score = GetStrongestLinkForPhotoId(imgPairs, photoId)
			print photoId, score
			if pair is not None:
				filteredImgPairs.append(pair)

	#Add two best photos
	filteredImgPairs.sort()
	filteredImgPairs.reverse()
	bestPair = filteredImgPairs[0]
	print "Using initial photos", bestPair[1], bestPair[2]

	cameraArrangement = CameraArrangement(filteredImgPairs)
	cameraArrangement.addedPhotos[bestPair[1]] = proj.RectilinearCam()
	cameraArrangement.addedPhotos[bestPair[2]] = proj.RectilinearCam()

	log.write("Starting with "+str(bestPair[1])+"\n")
	log.write("Starting with "+str(bestPair[2])+"\n")
	log.flush()

	cameraArrangement.OptimiseFit([bestPair[2]])

	visobj = visualise.VisualiseArrangement()
	
	while bestPair is not None:# and len(cameraArrangement.addedPhotos) < 5:
		bestPair, newInd = SelectPhotoToAdd(filteredImgPairs, cameraArrangement)
		if bestPair is None: continue
		print bestPair[:3], newInd
		
		if newInd:
			print "Adding", bestPair[2]
			photoToAdd = bestPair[2]
		else:
			print "Adding", bestPair[1]
			photoToAdd = bestPair[1]

		log.write("Adding "+str(photoToAdd)+"\n")
		log.flush()

		cameraArrangement.addedPhotos[photoToAdd] = proj.RectilinearCam()
		
		if 1:		
			cameraArrangement.OptimiseFit([photoToAdd])

		for photoId in cameraArrangement.addedPhotos:
			photo = cameraArrangement.addedPhotos[photoId]
			print photoId, photo.cLat, photo.cLon

		if 0:
			vis = visobj.Vis(poolPhotos, poolPath, filteredImgPairs, cameraArrangement)
			vis.save("vis{0}.png".format(len(cameraArrangement.addedPhotos)))

	if 1:
		print "Optimise all cameras"
		cameraArrangement.OptimiseFit(optRotation = True)

	pickle.dump(cameraArrangement.addedPhotos, open("camarr.dat","wb"), protocol=-1)

	log.flush()

	vis = visobj.Vis(poolPhotos, poolPath, filteredImgPairs, cameraArrangement)
	vis.save("vis{0}.png".format(len(cameraArrangement.addedPhotos)))

