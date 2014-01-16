'''
Copyright (c) 2013-2014, Tim Sheerman-Chase
All rights reserved.
'''

import glcamgui
import sys

if __name__ == '__main__':
	if 0:
		sys.stdout = open("mylog.txt", "wt")
		sys.stderr = open("myerr.txt", "wt")
	glcamgui.main()
