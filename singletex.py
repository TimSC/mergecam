
SCREEN_SIZE = (800, 600)

import math, v4l2cap, gltexture

from OpenGL.GL import *
from OpenGL.GLU import *

import pygame, ctypes, time
from pygame.locals import *
import numpy as np
from scipy import misc

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

	pbo = gltexture.GLReadPbo()

	while True:
		pbo.Prep(SCREEN_SIZE)

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

		start = time.clock()
		screen = pbo.Read(SCREEN_SIZE)
		print time.clock() - start
		if screen is not None:
			misc.imsave("test.jpg", screen)

if __name__ == "__main__":

	run()

