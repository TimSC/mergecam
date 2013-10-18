
import select, time, os, mjpeg, cStringIO
import v4l2capture
from v4l2 import *
from PIL import Image

class V4L2(object):
	def __init__(self):
		self.video = None
		self.size_x, self.size_y = None, None
		self.pixelFmt = None
		self.getFrameDuration = 0.
		self.huffTableDuration = 0.
		self.decodeJpegDuration = 0.

	def __del__(self):
		if self.video is not None:
			self.video.close()

	def Start(self, dev = None, reqSize=(640, 480), reqFps = 30, fmt = "MJPEG"):
		# Open the video device.
		if dev is None:
			dev = "/dev/video0"
		self.video = v4l2capture.Video_device(dev)

		# Suggest an image size to the device. The device may choose and
		# return another size if it doesn't support the suggested one.
		self.video.set_format(reqSize[0], reqSize[1], fmt)

		#Query current pixel format
		self.size_x, self.size_y, self.pixelFmt = self.video.get_format()

		#Set target frames per second
		self.fps = self.video.set_fps(reqFps)

		# Create a buffer to store image data in. This must be done before
		# calling 'start' if v4l2capture is compiled with libv4l2. Otherwise
		# raises IOError.
		self.video.create_buffers(10)

		# Send the buffer to the device. Some devices require this to be done
		# before calling 'start'.
		self.video.queue_all_buffers()

		# Start the device. This lights the LED if it's a camera that has one.
		self.video.start()

	def GetFrame(self, blocking=1):
		assert self.video is not None

		timeFunc = time.time()
		timeout = 1.
		if not blocking: timeout = 0.

		# Wait for the device to fill the buffer.
		ret = select.select((self.video,), (), (), timeout)

		if len(ret[0]) == 0:
			#Device timed out
			return None

		frame = None
		try:
			frame = self.video.read_and_queue(1)
		except Exception as err:
			return None

		#Decode frame
		if self.pixelFmt == "MJPEG":
			frame = list(frame)
			pixelData = frame[0]

			timeHuffmanTable = time.time()
			parseJpeg = mjpeg.ParseJpeg()
			fixedJpeg = cStringIO.StringIO()
			try:
				parseJpeg.InsertHuffmanTable(cStringIO.StringIO(pixelData), fixedJpeg)
				#fixedJpeg = pixelData
			except:
				print "MJPEG decoding failed"
				return None
			self.huffTableDuration += time.time() - timeHuffmanTable

			#print "jpeg len", len(fixedJpeg.getvalue())
			#Query current pixel format
			#self.size_x, self.size_y, self.pixelFmt = self.video.get_format()
			#print self.size_x, self.size_y, self.pixelFmt

			timeDecodeJpeg = time.time()
			#Decode image
			try:
				fixedJpeg.seek(0)
				im = Image.open(fixedJpeg)
				im = im.convert("RGB")
				frame[0] = im.tostring()
			except:
				frame[0] = None
			self.decodeJpegDuration += (time.time() - timeDecodeJpeg)

		else:
			print "Cannot decode pixel format", self.pixelFmt

		self.getFrameDuration += (time.time() - timeFunc)
		return frame


def ListDevices():
	file_names = [x for x in os.listdir("/dev") if x.startswith("video")]
	file_names.sort()

	out = []
	for file_name in file_names:
		path = "/dev/" + file_name
		print path
		try:
			video = v4l2capture.Video_device(path)
			driver, card, bus_info, capabilities = video.get_info()
			out.append((path, driver, card, bus_info, capabilities))
			
			video.close()
		except IOError as e:
			print e

	return out

if __name__=="__main__":

	devList = ListDevices()
	for dev in devList:
		print dev

	if len(devList) == 0:
		print "No capture device found"
		exit(0)

	v4l2 = V4L2()
	v4l2.Start(devList[0][0])

	while(1):
	
		data = v4l2.GetFrame()
		print len(data)
		if len(data) > 0:
			print len(data[0])
			fi = open("test.jpeg", "wb")
			fi.write(data[0])
			fi.flush()
			#im = Image.fromstring("RGB", (640, 480), data[0], 'jpeg', "RGB", '')

		time.sleep(0.001)




