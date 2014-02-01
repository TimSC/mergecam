'''
Copyright (c) 2013-2014, Tim Sheerman-Chase
All rights reserved.
'''

import glcamgui
import sys, os, argparse, StringIO

class NullConsole(object):
	def write(self, data):
		pass
	def read(self):
		return ""
	def flush(self):
		pass

if __name__ == '__main__':
	
	#parser = argparse.ArgumentParser(description='Merge live videos.')
	#parser.add_argument('--console', action='store_const', const=1, default=0, help='enable console')
	#args = parser.parse_args()

	#if not args.console:
	#	sys.stdout = NullConsole()
	#	sys.stderr = NullConsole()

	if 0:
		sys.stdout = open("mylog.txt", "wt")
		sys.stderr = open("myerr.txt", "wt")

	glcamgui.main(0)
