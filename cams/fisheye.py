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
		out = []
		for pt in ptsLatLon:

			#Convert lat lon to theta, ang
			screenX = math.tan(pt[1])
			screenDistOnGnd = (screenX**2+1.)**0.5
			screenY = math.tan(pt[0]) * screenDistOnGnd

			ang = math.atan2(screenX, screenY)
			radius = (screenX ** 2. + screenY ** 2.) ** 0.5
			R = math.atan2(radius, math.tan(self.vfov)) / math.atan(1.)
			
			#Apply camera lens adjustment
			dval = 1 - (self.a + self.b + self.c)
			correctionFunc = lambda x: (x ** 4) * self.a + (x ** 3) * self.b + (x ** 2) * self.c + x * dval
			Rcorrected = correctionFunc(R)

			#Calc centred image positions
			centImgX = Rcorrected * math.sin(ang) * (self.imgH / 2.)
			centImgY = Rcorrected * math.cos(ang) * (self.imgH / 2.)

			#Calc final position
			x = centImgX + (self.imgW / 2.) - self.d
			y = centImgY + (self.imgH / 2.) - self.e

			out.append((x, y))

		return out

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
			radius = math.tan(Rcorrected * math.atan(1.)) * math.tan(self.vfov)
			screenX = radius * math.sin(ang)
			screenY = radius * math.cos(ang)
			screenDistOnGnd = (screenX**2+1.)**0.5
			
			#Convert to lat and lon
			lon = math.atan(screenX)
			lat = math.atan2(screenY, screenDistOnGnd)
			out.append((lat, lon))

		return out



if __name__ == "__main__":
	
	x, y = 226.2789025152, 108.4201414704
	
	cam = FishEye()
	latLons = cam.UnProj([[x, y]])

	print [map(math.degrees, pt) for pt in latLons]

	pos2 = cam.Proj(latLons)

	print pos2

