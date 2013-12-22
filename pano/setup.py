#!/usr/bin/python
#
# 2013, Tim Sheerman-Chase
import os
from distutils.core import Extension, setup

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
			libraries = ["pthread", "freeglut", "glu32", "opengl32"],
			include_dirs=['C:\\Dev\\Lib\\freeglut-2.8.1\\include'],
			library_dirs=['C:\\Dev\\Lib\\freeglut-2.8.1\\lib'],
			)
		]
)

