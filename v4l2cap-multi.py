
import select, time
import v4l2capture, v4l2cap

if __name__=="__main__":

	devList = v4l2cap.ListDevices()

	v4l2 = [v4l2cap.V4L2() for dev in devList]

	for deviceObj, deviceParams in zip(v4l2, devList):
		print "Starting", deviceParams[0]
		deviceObj.Start(deviceParams[0])

	while(1):
		for deviceObj, deviceParams in zip(v4l2, devList):
			data = deviceObj.GetFrame(blocking=0)
			if data is not None:
				print deviceParams[0], len(data)
		time.sleep(0.01)


