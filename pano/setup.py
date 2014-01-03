#!/usr/bin/python
#
# 2013, Tim Sheerman-Chase
import os
from distutils.core import Extension, setup

if os.name == "nt":
	libs = ["pthread", "freeglut", "glu32", "opengl32"]
else:
	libs = ["pthread", "glut", "GLU", "GL"]


setup(
    name = "pano",
    version = "1.0",
    author = "Tim Sheerman-Chase",
    author_email = "info@kinatomic.com",
    url = "http://www.kinatomic.com",
    description = "Panoramic video",
    long_description = "Optimised panoramic video module for webcams.",
    license = "Proprietary",
    classifiers = [
        "License :: Proprietary",
        "Programming Language :: C++"],
    ext_modules = [
        Extension("pano", ["pano.cpp"], 
			libraries = libs,
			include_dirs=['C:\\Dev\\Lib\\freeglut-2.8.1\\include'],
			library_dirs=['C:\\Dev\\Lib\\freeglut-2.8.1\\lib'],
			)
		]
)

