import math
import scipy.optimize as optimize

class InvertableFunc(object):
	def __init__(self):
		self.x0 = 1.
		self.method = "Powell"
		self.func = lambda x: x ** 2

	def ErrEval(self, x, targety):
		err = abs(self.func(x)-targety)
		return err

	def InvFunc(self, y, verbose = 0):
		ret = optimize.minimize(self.ErrEval, self.x0, args=(y,), method=self.method)
		if verbose: print ret
		return ret.x

	def __call__(self, x):
		return self.func(x)

def ThetaAngToLatLon(theta, ang):
	scalex = math.sin(ang)
	scaley = math.cos(ang)
	oppOverAdj = math.tan(theta) #Ratio of radius and object distance

	objXOverScreenCentDist = scalex * oppOverAdj
	objYOverScreenCentDist = scaley * oppOverAdj
	screenDistOnGroundPlane = (objXOverScreenCentDist ** 2. + 1.) ** 0.5

	lon = math.atan(objXOverScreenCentDist)
	lat = math.atan2(objYOverScreenCentDist, screenDistOnGroundPlane)
	return lat, lon

def LatLonToThetaAng(lat, lon):
	objXOverScreenCentDist = math.tan(lon)
	screenDistOnGroundPlane = (objXOverScreenCentDist ** 2. + 1.) ** 0.5

	objYOverScreenCentDist = math.tan(lat) * screenDistOnGroundPlane
	optAxisDist = (objXOverScreenCentDist ** 2. + objYOverScreenCentDist ** 2.) ** 0.5
	theta = math.atan(optAxisDist)

	if objYOverScreenCentDist != 0.:
		if objXOverScreenCentDist != 0.:
			ang = math.atan2(objXOverScreenCentDist, objYOverScreenCentDist)
		else:
			if objYOverScreenCentDist > 0.:
				ang = 0.
			else:
				ang = math.pi
	else:
		if objXOverScreenCentDist == 0.:
			ang = 0.
		else:
			if objXOverScreenCentDist > 0.:
				ang = math.pi / 2.
			else:
				ang = -math.pi / 2.
	return theta, ang

# **************************************************************************

class FishEye(object):
	def __init__(self):
		self.imgW = 1280
		self.imgH = 1024
		self.a = 0.027
		self.b = 0.206
		self.c = -0.028
		self.d = -18
		self.e = -0.8
		self.vfov = math.radians(47.9)

	def Proj(self, ptsLatLon): #Lat, lon radians to image px

		pass

	def UnProj(self, ptsPix): #Image px to Lat, lon radians

		out = [] 
		for pt in ptsPix:
			#Centre image
			centImgX = pt[0] - (self.imgW / 2.) + self.d
			centImgY = pt[1] - (self.imgH / 2.) + self.e

			#Normalise positions
			centImgX2 = centImgX / (self.imgH / 2.)
			centImgY2 = centImgY / (self.imgH / 2.)

			#Calculate radius and angle
			R = (centImgX2 ** 2. + centImgY2 ** 2.) ** 0.5
			ang = math.atan2(centImgX2, centImgY2)
			
			#Apply lens correction function
			correctionFunc = InvertableFunc()
			dval = 1 - (self.a + self.b + self.c)
			correctionFunc.func = lambda x: (x ** 4) * self.a + (x ** 3) * self.b + (x ** 2) * self.c + x * dval
			Rcorrected = correctionFunc.InvFunc(R)

			#Calculate x and y in screen plane
			mag = math.tan(Rcorrected * math.atan(1.))
			screenXnorm = mag * math.sin(ang)
			screenYnorm = mag * math.cos(ang)
			screenX = screenXnorm * math.tan(self.vfov)
			screenY = screenYnorm * math.tan(self.vfov)
			screenDistOnGnd = (screenX**2+1.)**0.5
			
			#Convert to lat and lon
			lon = math.atan(screenX)
			lat = math.atan(screenX / screenDistOnGnd)
			out.append((lat, lon))

		return out



if __name__ == "__main__":
	
	x, y = 226.2789025152, 108.4201414704
	
	cam = FishEye()
	latLons = cam.UnProj([[x, y]])

	print [map(math.degrees, pt) for pt in latLons]

