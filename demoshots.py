
import proj, math
import scipy.misc as misc
import numpy as np

def GetSourceImg(inImg, src, cLon):
	print cLon

	dst = proj.Rectilinear()
	dst.imgW = 800
	dst.imgH = 600
	dst.hfov = 60
	dst.cLon = cLon

	outImg = np.zeros((dst.imgH, dst.imgW, 3), dtype=np.uint8)
	outPx = []
	for x in range(dst.imgW):
		for y in range(dst.imgH):
			outPx.append((x, y))
	worldPos = dst.UnProj(outPx)
	
	inPx = src.Proj(worldPos)
	#print inPx

	for ip, op in zip(inPx, outPx):
		try:
			outImg[op[1], op[0], :] = inImg[ip[1], ip[0], :]
		except IndexError:
			pass

	return outImg

if __name__=="__main__":

	inImg = misc.imread("tech/1439853045_a6f02c40be_o.jpg")

	src = proj.EquirectangularCam()
	src.imgW = inImg.shape[1]
	src.imgH = inImg.shape[0]
	
	src.hFov = math.radians(140.0)
	src.vFov = src.hFov * float(inImg.shape[0]) / float(inImg.shape[1])

	outImg = GetSourceImg(inImg, src, math.radians(-30))
	misc.imsave("test1.png", outImg)

	outImg = GetSourceImg(inImg, src, math.radians(0))
	misc.imsave("test2.png", outImg)
	
	outImg = GetSourceImg(inImg, src, math.radians(30))
	misc.imsave("test3.png", outImg)

