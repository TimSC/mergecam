
import proj, math
import numpy as np
from PIL import Image, ImageDraw

class VisualiseArrangement(object):

	def __init__(self):

		self.imSize = (800, 600)
		self.eqRect = proj.EquirectangularCam()
		self.eqRect.imgW = self.imSize[0]
		self.eqRect.imgH = self.imSize[1]

		self.pix = []
		for x in range(self.imSize[0]):
			for y in range(self.imSize[1]):
				self.pix.append((x, y))
		self.pixWorld = np.array(self.eqRect.UnProj(self.pix), dtype=np.float64)

	def VisImages(self, frames, metas, imgPairs, cameraArrangement, im, iml):

		#For each photo
		for photoId in cameraArrangement.addedPhotos.keys():
			#Project world positions into this camera's image space
			camParams = cameraArrangement.addedPhotos[photoId]
			meta = metas[int(photoId)]
			imPos = camParams.Proj(self.pixWorld)
			#camImg = Image.open(poolPath+"/"+photoId)
			assert meta['format'] == "RGB24"
			camImg = Image.frombuffer("RGB", (meta['width'], meta['height']), str(frames[photoId]), 'raw', "RGB", 0, 1)
			camImgl = camImg.load()
		
			self.VisImageSingle(camParams, camImgl, iml, imPos)

	def VisImageSingle(self, camParams, camImgl, iml, imPos):

		#Check which are valid pixels within bounds
		for imIn, imOut in zip(imPos, self.pix):
			if imIn[0] < 0 or imIn[0] >= camParams.imgW: continue
			if imIn[1] < 0 or imIn[1] >= camParams.imgH: continue
			
			#Copy pixel to output
			if not math.isnan(imIn[0]):
				iml[imOut[0], imOut[1]] = camImgl[imIn[0], imIn[1]]

	def VisImageOutlines(self, calibrationFrames, calibrationMeta, imgPairs, cameraArrangement, im, iml):

		for photoId in cameraArrangement.addedPhotos.keys():
			camParams = cameraArrangement.addedPhotos[photoId]
			imgEdgePts = [(0,0),(camParams.imgW,0),(camParams.imgW,camParams.imgH),(0, camParams.imgH)]
			worldPts = camParams.UnProj(imgEdgePts)
			imgPts = self.eqRect.Proj(worldPts)

			#Draw bounding box
			draw = ImageDraw.Draw(im) 
			for i in range(len(imgPts)):
				pt1 = list(imgPts[i])
				pt2 = list(imgPts[(i+1)%len(imgPts)])
				draw.line(pt1+pt2, fill=128)
			del draw

	def Vis(self, calibrationFrames, calibrationMeta, imgPairs, cameraArrangement):

		im = Image.new("RGB", self.imSize)
		iml = im.load()

		self.VisImages(calibrationFrames, calibrationMeta, imgPairs, cameraArrangement, im, iml)
		self.VisImageOutlines(calibrationFrames, calibrationMeta, imgPairs, cameraArrangement, im, iml)

		return im

