
import select, time, os
import v4l2capture

class V4L2(object):
	def __init__(self):
		self.video = None

	def __del__(self):
		if self.video is not None:
			self.video.close()

	def Start(self, dev = None, reqSize=(640, 480), reqFps = 30):
		# Open the video device.
		if dev is None:
			dev = "/dev/video0"
		self.video = v4l2capture.Video_device(dev)

		# Suggest an image size to the device. The device may choose and
		# return another size if it doesn't support the suggested one.
		yuv420 = 1
		self.size_x, self.size_y = self.video.set_format(reqSize[0], reqSize[1], yuv420)

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

		if blocking:
			# Wait for the device to fill the buffer.
			select.select((self.video,), (), ())

		try:
			return self.video.read_and_queue(1)
		except Exception as err:
			return None

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
		time.sleep(0.001)




