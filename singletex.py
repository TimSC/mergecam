
SCREEN_SIZE = (800, 600)

import math, v4l2cap, gltexture

from OpenGL.GL import *
from OpenGL.GLU import *

import pygame, ctypes
from pygame.locals import *
import numpy as np
from scipy import misc

import OpenGL.raw.GL as rawgl
import OpenGL.GL.ARB.pixel_buffer_object as pbo

### OpenGL Utility Functions

def resize(width, height):
	
	glViewport(0, 0, width, height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluPerspective(60.0, float(width)/height, .001, 1000.)
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

def init():
	
	glEnable(GL_DEPTH_TEST)
	glDepthFunc(GL_LEQUAL)
	glClearColor(1.0, 1.0, 1.0, 0.0)

	# set up texturing
	glEnable(GL_TEXTURE_2D)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

### Main Program

def run():
	
	pygame.init()
	screen = pygame.display.set_mode(SCREEN_SIZE, HWSURFACE|OPENGL|DOUBLEBUF)
	
	resize(*SCREEN_SIZE)
	init()
	
	clock = pygame.time.Clock()
	
	glMaterial(GL_FRONT, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))	
	glMaterial(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

	v4l2 = v4l2cap.V4L2()
	v4l2.Start()

	pboSupported = pbo.glInitPixelBufferObjectARB()
	print "pboSupported", pboSupported

	while True:
		
		time_passed = clock.tick()
		time_passed_seconds = time_passed / 1000.

		for event in pygame.event.get():
			if event.type == QUIT:
				return
			if event.type == KEYUP and event.key == K_ESCAPE:
				return

		pressed = pygame.key.get_pressed()

		img = v4l2.GetFrame()[0]
		tex = gltexture.GLTexture()
		tex.SetFromString(img, v4l2.size_x, v4l2.size_y)

		# Clear the screen, and z-buffer
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
						
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()

		gluLookAt(0., 0., 10., # look from camera XYZ
			0., 0., 0., # look target
			0., 1., 0.); # up

		tex.Draw()

		# Show the screen
		pygame.display.flip()

		del tex

		output_texture = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, output_texture)
		# set basic parameters
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

		data = np.zeros((v4l2.size_x*v4l2.size_y,4),np.uint8)
		dest_pbo = glGenBuffers(1)
		glBindBuffer(GL_ARRAY_BUFFER, dest_pbo)
		glBufferData(GL_ARRAY_BUFFER, data, GL_DYNAMIC_DRAW)
		glBindBuffer(GL_ARRAY_BUFFER, 0)

		glBindBuffer(pbo.GL_PIXEL_UNPACK_BUFFER_ARB, dest_pbo)
		
		x = glReadPixels(0,0,SCREEN_SIZE[0],SCREEN_SIZE[1],GL_RGBA, GL_UNSIGNED_BYTE)
		xa = np.fromstring(x, np.uint8).reshape((SCREEN_SIZE[1],SCREEN_SIZE[0],4))
		xa = xa[::-1,:] #Flip vertically
		misc.imsave("test.png", xa)

		glBindBuffer(pbo.GL_PIXEL_UNPACK_BUFFER_ARB, 0);

		glBindBuffer(GL_ARRAY_BUFFER, dest_pbo)
		glDeleteBuffers(1, [dest_pbo]);

if __name__ == "__main__":

	run()

