
import struct

class ParseJpeg(object):
	def __init__(self):
		pass

	def Open(self, fiHandle):
		#http://www.gdcl.co.uk/2013/05/02/Motion-JPEG.html
		
		data = fiHandle.read()
		parsing = True
		frameStartPos = 0
		huffFound = False
		while parsing:
			#Check if we should stop
			if frameStartPos >= len(data):
				parsing = False
				continue

			#Read the next frame
			twoBytes, frameStartPos, frameEndPos = self.ReadFrame(data, frameStartPos)
			print map(hex, twoBytes), frameStartPos, frameEndPos

			#Check the type of frame
			if twoBytes[0] == 0xff and twoBytes[1] == 0xc4:
				huffFound = True

			#Move cursor
			frameStartPos = frameEndPos

		print "huffFound", huffFound

	def ReadFrame(self, data, offset):
		cursor = offset
		#Check frame start
		frameStartPos = offset
		twoBytes = struct.unpack_from("BB", data, cursor)
		#print map(hex, twoBytes)
		cursor += 2
		
		#Handle padding
		paddingByte = twoBytes[0] == 0xff and twoBytes[1] == 0xff
		if paddingByte: return twoBytes, frameStartPos, cursor

		#Reset markers and start/end of frame
		frameStart = twoBytes[0] == 0xff and twoBytes[1] >= 0xd0 and twoBytes[1] <= 0xd9
		if frameStart: return twoBytes, frameStartPos, cursor

		#Determine length of compressed (entropy) data
		compressedDataStart = twoBytes[0] == 0xff and twoBytes[1] == 0xda
		if compressedDataStart:
			#Seek through frame
			run = True
			while run:
				byte = struct.unpack_from("B", data, cursor)[0]
				cursor += 1
			
				if byte == 0xff:
					byte2 = struct.unpack_from("B", data, cursor)[0]
					cursor += 1
					if byte2 != 0x00:
						#End of frame
						run = 0
						cursor -= 2
			return twoBytes, frameStartPos, cursor

		#More cursor for all other segment types
		segLength = struct.unpack_from(">H", data, cursor)[0]
		#print "segLength", segLength
		cursor += segLength
		
		return twoBytes, frameStartPos, cursor

if __name__ == "__main__":

	pj = ParseJpeg()
	#pj.Open(open("test.mjpeg","rb"))
	pj.Open(open("IMG_6618.JPG","rb"))

	
