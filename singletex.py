
SCREEN_SIZE = (800, 600)

import math, v4l2cap, gltexture

from OpenGL.GL import *
from OpenGL.GLU import *

import pygame, ctypes, time
from pygame.locals import *
import numpy as np
from scipy import misc
import cv2

### OpenGL Utility Functions

def resize(width, height):
	
	glViewport(0, 0, width, height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluPerspective(60.0, float(width)/height, .001, 1000.)
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

def init():
	
	glDisable(GL_DEPTH_TEST)
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

	pbo = gltexture.GLReadPbo(SCREEN_SIZE)

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

		if 0:
			imgNp = np.fromstring(img, np.uint8)
			imgNp = imgNp.reshape((v4l2.size_y, v4l2.size_x, 3))
			#detector = cv2.FeatureDetector_create("STAR")
			#detector = cv2.FeatureDetector_create("FAST")
			#detector = cv2.FeatureDetector_create("ORB")
			#detector = cv2.FeatureDetector_create("MSER")
			detector = cv2.FeatureDetector_create("GFTT")

			#detector = cv2.FastFeatureDetector(threshold=50)
			#detector = cv2.GoodFeaturesToTrackDetector(200)
			#detector = cv2.OrbFeaturesFinder()

			descriptor = cv2.DescriptorExtractor_create("ORB")

			#matcher = cv2.FlannBasedMatcher()

		grey = cv2.cvtColor(imgNp,cv2.COLOR_BGR2GRAY)
		keypoints = detector.detect(grey)
		(keypoints, descriptors) = descriptor.compute(grey, keypoints)

		# Clear the screen, and z-buffer
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
						
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()

		gluLookAt(0., 0., 10., # look from camera XYZ
			0., 0., 0., # look target
			0., 1., 0.); # up

		tex.Draw()

		if 0:
			for pt in keypoints:
				glDisable(GL_TEXTURE_2D)
				glColor4f(1.,0.,0.,1.)
				glBegin(GL_LINES)
				x = pt.pt[0] * 10. / v4l2.size_x - 5.
				y = - pt.pt[1] * 10. / v4l2.size_y + 5.
				glVertex(-0.3+x,0.+y,0.)
				glVertex(0.3+x,0.+y,0.)
				glVertex(0.+x,-0.3+y,0.)
				glVertex(0.+x,0.3+y,0.)
				glEnd()

		# Show the screen
		pygame.display.flip()

		del tex

		start = time.clock()
		screen = pbo.Read()
		print time.clock() - start
		if screen is not None:
			misc.imsave("test.jpg", screen)

if __name__ == "__main__":

	run()

