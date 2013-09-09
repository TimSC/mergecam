
import pickle, proj, os, math
import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as optimize
from PIL import Image, ImageDraw

class CameraArrangement(object):
	def __init__(self, imgPairs):
		self.imgPairs = imgPairs
		self.addedPhotos = {}

	def OptimiseFit(self, photToOpt = None):

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

		print initialVals

		if 0:
			final = optimize.minimize(self.Eval, initialVals, (0, initialValKey, photToOpt), method="Powell")
			print "score", final.x, final.fun
		if 1:
			final = optimize.leastsq(self.Eval, initialVals, (1, initialValKey, photToOpt))
			print "score", final
			finalVals = final[0]

		#Set values
		for phot in initialValKey:
			params = initialValKey[phot]
			self.addedPhotos[phot].cLat = finalVals[params["lat"]]
			self.addedPhotos[phot].cLon = finalVals[params["lon"]]

	def Eval(self, vals, separateTerms, initialValKey, photToOpt):

		dists = []
		countPairs = 0
		weightThreshold = 0.2

		while len(dists) == 0:
			for pair in self.imgPairs:
				weight = pair[0]
				if weight < weightThreshold: continue #Discard poor pairings

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

				camModel2 = self.addedPhotos[fina2]
				if fina2 in initialValKey:
					camModel2.cLat = vals[initialValKey[fina2]["lat"]]
					camModel2.cLon = vals[initialValKey[fina2]["lon"]]

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

			if len(dists) == 0:
				weightThreshold /= 2
				print "Reducing threshold to", weightThreshold

		#print vals, score
		#print countPairs

		if separateTerms:
			return dists
		score = np.array(dists).mean()
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

def VisualiseArrangement(poolPhotos, poolPath, imgPairs, cameraArrangement):

	im = Image.new("RGB", (800, 600))
	iml = im.load()
	eqRect = proj.EquirectangularCam()
	eqRect.imgW = im.size[0]
	eqRect.imgH = im.size[1]

	pix = []
	for x in range(im.size[0]):
		for y in range(im.size[1]):
			pix.append((x, y))

	pixWorld = eqRect.UnProj(pix)
	#For each photo
	for photoId in cameraArrangement.addedPhotos.keys():
		#Project world positions into this camera's image space
		camParams = cameraArrangement.addedPhotos[photoId]
		imPos = camParams.Proj(pixWorld)
		camImg = Image.open(poolPath+"/"+photoId)
		camImgl = camImg.load()
		
		#Check which are valid pixels within bounds
		for imIn, imOut in zip(imPos, pix):
			if imIn[0] < 0 or imIn[0] >= camParams.imgW: continue
			if imIn[1] < 0 or imIn[1] >= camParams.imgH: continue
			
			#Copy pixel to output
			if not math.isnan(imIn[0]):
				iml[imOut[0], imOut[1]] = camImgl[imIn[0], imIn[1]]

	for photoId in cameraArrangement.addedPhotos.keys():
		camParams = cameraArrangement.addedPhotos[photoId]
		imgEdgePts = [(0,0),(camParams.imgW,0),(camParams.imgW,camParams.imgH),(0, camParams.imgH)]
		worldPts = camParams.UnProj(imgEdgePts)
		imgPts = eqRect.Proj(worldPts)

		#Draw bounding box
		draw = ImageDraw.Draw(im) 
		for i in range(len(imgPts)):
			pt1 = list(imgPts[i])
			pt2 = list(imgPts[(i+1)%len(imgPts)])
			draw.line(pt1+pt2, fill=128)
		del draw

	return im


if __name__=="__main__":
	imgPairs = pickle.load(open("imgpairs.dat", "rb"))

	poolPath = "/home/tim/dev/glcamdata/house"
	poolPhotos = os.listdir(poolPath)

	log = open("log.txt", "wt")
	
	#Add two best photos
	imgPairs.sort()
	imgPairs.reverse()
	bestPair = imgPairs[0]
	print "Using initial photos", bestPair[1], bestPair[2]

	cameraArrangement = CameraArrangement(imgPairs)
	cameraArrangement.addedPhotos[bestPair[1]] = proj.RectilinearCam()
	cameraArrangement.addedPhotos[bestPair[2]] = proj.RectilinearCam()

	log.write("Starting with "+str(bestPair[1])+"\n")
	log.write("Starting with "+str(bestPair[2])+"\n")
	log.flush()

	cameraArrangement.OptimiseFit([bestPair[2]])
	
	while bestPair is not None:
		bestPair, newInd = SelectPhotoToAdd(imgPairs, cameraArrangement)
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
		
		cameraArrangement.OptimiseFit([photoToAdd])

		for photoId in cameraArrangement.addedPhotos:
			photo = cameraArrangement.addedPhotos[photoId]
			print photoId, photo.cLat, photo.cLon

		vis = VisualiseArrangement(poolPhotos, poolPath, imgPairs, cameraArrangement)
		vis.save("vis{0}.png".format(len(cameraArrangement.addedPhotos)))

	pickle.dump(cameraArrangement.addedPhotos, open("camarr.dat","wb"), protocol=-1)

	log.flush()


