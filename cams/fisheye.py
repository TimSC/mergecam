import math
import scipy.optimize as optimize
import numpy as np

class InvertableFunc(object):
	def __init__(self):
		self.x0 = 1.
		self.method = "Powell"
		self.func = lambda x: x ** 2

	def ErrEval(self, x, targety):
		err = abs(self.func(x)-targety)
		return err

	def InvFuncByOptimize(self, y, verbose = 0):
		ret = optimize.minimize(self.ErrEval, self.x0, args=(y,), method=self.method)
		if verbose: print ret
		return ret.x

	def EvalPolyInv(self, comp, xvals, yvals):
		total = np.zeros(len(xvals))
		for i, c in enumerate(comp):
			total += np.power(yvals, i) * c
		err = np.abs(total - np.array(xvals))
		toterr = err.sum()
		print toterr
		return toterr

	def EstimatePolyInv(self, minx, maxx, numPoints = 1000, numComp=6):
		xvals = np.linspace(minx, maxx, numPoints)
		yvals = []
		prevy = None
		for x in xvals:
			y = self.func(x)
			if prevy is not None or y >= prevy:
				yvals.append(y)
			else:
				break
			prevy = y

		#import matplotlib.pyplot as plt
		#plt.plot(xvals, yvals)
		#plt.show()

		comp = np.ones(numComp)
		ret = optimize.minimize(self.EvalPolyInv, comp, args=(xvals, yvals), method=self.method)
		print ret

		ytest = np.linspace(min(yvals), max(yvals), numPoints)
		xtest = []
		for y in ytest:
			tot = 0.
			for i, c in enumerate(ret.x):
				tot += (y ** i) * c
			xtest.append(tot)

		import matplotlib.pyplot as plt
		plt.plot(yvals, xvals)
		plt.plot(ytest, xtest)
		plt.show()

	def __call__(self, x):
		return self.func(x)

# **************************************************************************

class FishEye(object):
	def __init__(self):
		self.imgW = 1280
		self.imgH = 1024
		self.a = 0.02694
		self.b = 0.20635
		self.c = -0.02845
		self.d = +18. / 1280.
		self.e = -0.8 / 1024.
		self.hfov = 118.75
		self.halfVfov = self.imgH * math.radians(self.hfov / 2.) / self.imgW
		self.cLat = 0.
		self.cLon = 0.

	def Proj(self, ptsLatLon): #Lat, lon radians to image px
		out = []
		for pt in ptsLatLon:

			#Convert lat lon to theta, ang
			screenX = math.tan(pt[1] - self.cLon)
			screenDistOnGnd = (screenX**2+1.)**0.5
			screenY = math.tan(pt[0] - self.cLat) * screenDistOnGnd

			ang = math.atan2(screenX, screenY)
			radius = (screenX ** 2. + screenY ** 2.) ** 0.5
			R = math.atan2(radius, math.tan(self.halfVfov)) / math.atan(1.)
			
			print "a1", ang, R

			#Apply camera lens adjustment
			dval = 1 - (self.a + self.b + self.c)
			correctionFunc = InvertableFunc()
			correctionFunc.func = lambda x: (x ** 4) * self.a + (x ** 3) * self.b + (x ** 2) * self.c + x * dval
			#correctionFunc = lambda x: (x ** 4) * self.a + (x ** 3) * self.b + (x ** 2) * self.c + x * dval
			correctionFunc.EstimatePolyInv(0.,3.)
			exit(0)
			Rcorrected = correctionFunc.InvFunc(R)

			print "a2", Rcorrected

			#Calc centred image positions
			centImgX = Rcorrected * math.sin(ang) * (self.imgH / 2.)
			centImgY = Rcorrected * math.cos(ang) * (self.imgH / 2.)

			print "a3", centImgX, centImgY

			#Calc final position
			x = centImgX + (self.imgW / 2.) - self.d * self.imgW
			y = centImgY + (self.imgH / 2.) - self.e * self.imgH

			out.append((x, y))

		return out

	def UnProj(self, ptsPix): #Image px to Lat, lon radians

		out = [] 
		for pt in ptsPix:
			#Centre image
			centImgX = pt[0] - (self.imgW / 2.) + self.d * self.imgW
			centImgY = pt[1] - (self.imgH / 2.) + self.e * self.imgH

			print "b3", centImgX, centImgY

			#Normalise positions
			centImgX2 = centImgX / (self.imgH / 2.)
			centImgY2 = centImgY / (self.imgH / 2.)

			#Calculate radius and angle
			R = (centImgX2 ** 2. + centImgY2 ** 2.) ** 0.5
			ang = math.atan2(centImgX2, centImgY2)
			
			print "b2", R

			#Apply lens correction function
			dval = 1 - (self.a + self.b + self.c)
			#correctionFunc = InvertableFunc()
			#correctionFunc.func = lambda x: (x ** 4) * self.a + (x ** 3) * self.b + (x ** 2) * self.c + x * dval
			correctionFunc = lambda x: (x ** 4) * self.a + (x ** 3) * self.b + (x ** 2) * self.c + x * dval
			Rcorrected = correctionFunc(R)

			print "b1", ang, Rcorrected

			#Calculate x and y in screen plane
			radius = math.tan(Rcorrected * math.atan(1.)) * math.tan(self.halfVfov)
			screenX = radius * math.sin(ang)
			screenY = radius * math.cos(ang)
			screenDistOnGnd = (screenX**2+1.)**0.5
			
			#Convert to lat and lon
			lon = math.atan(screenX) + self.cLon
			lat = math.atan2(screenY, screenDistOnGnd) + self.cLat
			out.append((lat, lon))

		return out



if __name__ == "__main__":
	
	x, y = 226.2789025152, 108.4201414704


	cam = FishEye()
	latLons = cam.UnProj([[x, y]])

	print [map(math.degrees, pt) for pt in latLons]

	pos2 = cam.Proj(latLons)

	print pos2

