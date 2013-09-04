
import select, time
import v4l2capture

class V4L2(object):
	def __init__(self):
		self.video = None

	def __del__(self):
		if self.video is not None:
			self.video.close()

	def Start(self, dev = None):
		# Open the video device.
		if dev is None:
			dev = "/dev/video0"
		self.video = v4l2capture.Video_device(dev)

		# Suggest an image size to the device. The device may choose and
		# return another size if it doesn't support the suggested one.
		#self.size_x, self.size_y = self.video.set_format(1280, 1024)
		self.size_x, self.size_y = self.video.set_format(640, 480)

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


if __name__=="__main__":

	v4l2 = V4L2()
	v4l2.Start()

	while(1):
	
		data = v4l2.GetFrame()
		print len(data)
		time.sleep(0.001)




