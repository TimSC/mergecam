
import select, time
import v4l2capture, v4l2cap

if __name__=="__main__":

	devList = v4l2cap.ListDevices()

	v4l2 = [v4l2cap.V4L2() for dev in devList]
	frameTimes = {}
	showRateTime = None

	for deviceObj, deviceParams in zip(v4l2, devList):
		print "Starting", deviceParams[0]
		deviceObj.Start(deviceParams[0], fmt="MJPEG")

	while(1):
		for deviceObj, deviceParams in zip(v4l2, devList):
			devName = deviceParams[0]
			data = deviceObj.GetFrame(blocking=1)
			if data is not None:
				#print time.time(), devName, len(data)

				#Store time when frame arrives
				if devName not in frameTimes:
					frameTimes[devName] = []
				frameTimes[devName].append(time.time())
				while len(frameTimes[devName]) > 10:
					frameTimes[devName].pop(0)

		if showRateTime is None or showRateTime + 1. < time.time():
			#Estimate frame rates
			for devName in frameTimes:
				devTimes = frameTimes[devName]
				elapse = time.time() - devTimes[0]
				if elapse == 0.: continue
				rate = len(devTimes) / elapse
				print devName, rate

			showRateTime = time.time()

		time.sleep(0.01)


