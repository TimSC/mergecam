#!/usr/bin/python
#
# 2013, Tim Sheerman-Chase
import os
from distutils.core import Extension, setup

debug = 0
c_args=[]
l_args=[]
	
if os.name == "nt":
	#if debug:
	#	c_args=['/Zi', '/EHsc']
	#	l_args=["/MANIFEST", "/DEBUG"]
	#else:
	#	c_args=[]
	#	l_args=["/MANIFEST"]
	libs = ["pthreadVC2", "freeglut", "glu32", "opengl32"]
else:
	libs = ["pthread", "glut", "GLU", "GL"]

#SET VS90COMNTOOLS=%VS100COMNTOOLS%
#python setup.py build -c msvc
#python setup.py install

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
			include_dirs=['C:\\Dev\\Lib\\freeglut-2.8.1\\include', "C:\\Dev\\Lib\\pthreads\\pthreads.2"],
			library_dirs=['C:\\Dev\\Lib\\freeglut-2.8.1\\lib\\x86', "C:\\Dev\\Lib\\pthreads\\pthreads.2"],
			extra_compile_args=c_args,
			extra_link_args=l_args,
			)
		]
)

