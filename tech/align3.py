
import pickle
import matplotlib.pyplot as plt

if __name__=="__main__":

	imgPairs = pickle.load(open("imgpairs.dat", "rb"))
	camArr = pickle.load(open("camarr.dat", "rb"))

	for photoId in camArr:
		photo = camArr[photoId]
		plt.plot(photo.rectilinear.cLon, photo.rectilinear.cLat,'x')
		print photoId, photo.rectilinear.cLat, photo.rectilinear.cLon
		
	plt.show()

