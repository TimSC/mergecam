
import math

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

import OpenGL.GL.ARB.texture_non_power_of_two as npot
import OpenGL.GL.ARB.pixel_buffer_object as pbo

def IsPowerOfTwo(x):
    return (int(x) & (int(x) - 1)) == 0

class GLTexture(object):
	def __init__(self):
		self.num = None
		self.supportsNpot = npot.glInitTextureNonPowerOfTwoARB()

	def __del__(self):
		if self.num is not None:
			glDeleteTextures([self.num])
		self.num = None

	def SetFromMatrix(self, img):
		img = np.array(img)
		rawData = img.astype('uint8').tostring()
		self.SetFromString(rawData, img.shape[1], img.shape[0])

	def SetFromString(self, img, w, h):
		if not IsPowerOfTwo(w) and not self.supportsNpot:
			raise Exception("Texture dimensions must be power of 2")
		if not IsPowerOfTwo(h) and not self.supportsNpot:
			raise Exception("Texture dimensions must be power of 2")

		self.num = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, self.num)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB,
			GL_UNSIGNED_BYTE, img)

	def Draw(self):
		assert self.num is not None

		glEnable(GL_TEXTURE_2D)
		glBindTexture(GL_TEXTURE_2D, self.num)
		glColor3f(0.98, 0.96, 0.95)

		glBegin(GL_POLYGON)

		glTexCoord2f(0.,1.)
		glVertex(-5.,-5.,0.)

		glTexCoord2f(0.,0.)
		glVertex(-5.,5.,0.)

		glTexCoord2f(1.,0.)
		glVertex(5.,5.,0.)

		glTexCoord2f(1.,1.)
		glVertex(5.,-5.,0.)
		
		glEnd()

class GLReadPbo(object):
	def __init__(self):
		self.pboSupported = pbo.glInitPixelBufferObjectARB()

	def __del__(self):
		pass

	def Read(self, capSize):
		if not self.pboSupported:
			return self.ReadSlow()

		self.destpbo = glGenBuffers(1)
		glBindBuffer(pbo.GL_PIXEL_UNPACK_BUFFER_ARB, self.destpbo)
		
		px = glReadPixels(0, 0, capSize[0], capSize[1], GL_RGBA, GL_UNSIGNED_BYTE)
		xa = np.fromstring(px, np.uint8).reshape((capSize[1],capSize[0],4))
		xa = xa[::-1,:] #Flip vertically

		#glBindBuffer(pbo.GL_PIXEL_UNPACK_BUFFER_ARB, 0)

		glBindBuffer(pbo.GL_PIXEL_UNPACK_BUFFER_ARB, 0)
		glDeleteBuffers(1, [self.destpbo])
		return xa

	def ReadSlow(self, capSize):
		glBindBuffer(pbo.GL_PIXEL_UNPACK_BUFFER_ARB, 0)
		px = glReadPixels(0, 0, capSize[0], capSize[1], GL_RGBA, GL_UNSIGNED_BYTE)
		xa = np.fromstring(px, np.uint8).reshape((capSize[1],capSize[0],4))
		xa = xa[::-1,:] #Flip vertically
		return xa

