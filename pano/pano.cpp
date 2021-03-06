// python-v4l2capture
// Python extension to capture video with video4linux2
//
// 2009, 2010, 2011 Fredrik Portstrom, released into the public domain
// 2011, Joakim Gebart
// 2013, Tim Sheerman-Chase
// See README for license

#define USE_LIBV4L

#include <Python.h>
#include <string.h>
#include <stdio.h>
#include <string>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <map>
#include <vector>
#include <stdexcept>
#include <pthread.h>
#include <time.h>
#include <math.h>
#include <GL/glut.h>
#include <GL/glu.h>
#include <GL/freeglut.h>

int gGlutInitDone = 0;

class PanoView_cl{
public:
	PyObject_HEAD

	long outImgW, outImgH;
	PyObject *timeModule;
	PyObject *timeFunc;
	PyObject *cameraArrangement;
	PyObject *outProjection;
	std::vector<GLuint> displayLists;
	int nonPowerTwoTexSupported;
	std::vector<GLuint> textureIds;
	std::vector<int> openglTxWidthLi, openglTxHeightLi;
	int dstXRangeSet, dstYRangeSet;
	double dstXMin, dstXMax;
	double dstYMin, dstYMax;
	std::vector<int> displayListImgWidth, displayListImgHeight;
	std::vector<std::map<int, std::vector<double> > > samplePoints;
	std::vector<double> camBrightnessLi;
	bool blend, autoBright;

	std::vector<char *> srcImgRawLi;
	std::vector<unsigned> srcImgRawLenLi;
	std::vector<long> srcHeightLi, srcWidthLi;
	std::vector<std::string> srcFmtLi;
	std::vector<PyObject *> srcPyImage, srcMetaObj;

};
typedef PanoView_cl PanoView;

static PyObject *TestFunc(PyObject *self, PyObject *args)
{
	Py_RETURN_NONE;
}

// Calculates log2 of number.  
double Log2( double n )  
{  
    // log(n)/log(2) is log2.  
    return log( n ) / log( 2. );  
}

int ResizeToPowersOfTwo(unsigned char *imgRaw, 
	long sourceWidth, long sourceHeight, 
	const char *sourceFmt, 
	unsigned char **outBuff, unsigned *openglTexLen,
	unsigned *openglTxWidth, unsigned *openglTxHeight)
{
	if(strcmp(sourceFmt, "RGB24") != 0 &&
		strcmp(sourceFmt, "BGR24"))
		return 0; //Unsupported format
	if(outBuff == NULL || openglTexLen == NULL || openglTxWidth == NULL || openglTxHeight == NULL)
		throw std::runtime_error("An output pointer is null");

	int roundWidth = pow(2., (int)ceil(Log2(sourceWidth)));
	int roundHeight = pow(2., (int)ceil(Log2(sourceHeight)));
	int requiredMem = roundWidth * roundHeight * 3;

	*openglTxWidth = roundWidth;
	*openglTxHeight = roundHeight;

	//Establish output buffer
	if(*outBuff != NULL && requiredMem != *openglTexLen)
		throw std::runtime_error("Output buffer has incorrect size");
	*openglTexLen = requiredMem;
	if(*outBuff==NULL)
	{
		*outBuff = new unsigned char[requiredMem];
	}
	memset(*outBuff, 0x00, requiredMem);

	//Copy data to output buff
	for(long x = 0 ; x < sourceWidth; x++)
	{
		for(long y = 0; y < sourceHeight; y++)
		{
			int inputOffset = y * sourceWidth * 3 + x * 3;
			int outputOffset = y * roundWidth * 3 + x * 3;
			for(char ch = 0; ch < 3; ch++)
				(*outBuff)[outputOffset + ch] = imgRaw[inputOffset + ch];
		}
	}

	return 1;
}

void PrintGlErrors(const char *codeLocation)
{	
	GLenum err = glGetError();
	while(err!=GL_NO_ERROR)
	{
		std::cout << "opengl error ("<<codeLocation<<"): " << gluErrorString(err) << std::endl;
		err = glGetError();
	}
}

void GlutWindowCloseEvent()
{
	std::cout << "GlutWindowCloseEvent()" << std::endl;
	exit(0);
}

int FindStringInVector(const char *needle, std::vector<std::string> haystack)
{
	for(unsigned int i=0;i<haystack.size();i++)
	{
		std::string &ext = haystack[i];
		int hit = ext.compare(needle);
		if(!hit) return true;
	}
	return false;
}

std::vector<double> GetPixFromRawBuff(const unsigned char* buff, unsigned buffLen, long width, long height, 
	double x, double y, const char *pxFmt)
{
	if(strcmp(pxFmt, "RGB24")!=0)
		throw std::runtime_error("Unsupported pixel format");
	std::vector<double> out;

	//Nearest neighbour pixel	
	int rx = (int)(x + 0.5);
	int ry = (int)(y + 0.5);

	if(rx < 0 || rx >= width || ry < 0 || ry >= height)
		throw std::runtime_error("Out of image bounds");

	unsigned tupleOffset = rx * 3 + ry * width * 3;
	if(tupleOffset < 0 || tupleOffset+2 >= buffLen)
		throw std::runtime_error("Out of image buffer bounds");

	out.push_back(buff[tupleOffset]);
	out.push_back(buff[tupleOffset+1]);
	out.push_back(buff[tupleOffset+2]);
	return out;
}

double VecRgbToGrey(std::vector<double> &col)
{
	return 0.2126 * col[0] + 0.7152  * col[1] + 0.0722 * col[2];
}

double VecAverage(std::vector<double> &vals)
{
	//TODO Not very good way to calc average!
	double total = 0;
	for(unsigned i=0;i<vals.size();i++)
		total += vals[i];
	return total / (double)(vals.size());
}

double CompareCameraBrightness(int currentCam, PanoView *self, 
	std::vector<std::map<int, std::vector<double> > > &sampleColsLi)
{
	std::vector<double> currentCamGreyLi;
	std::vector<double> otherCamGreyLi;
	for(unsigned ptNum = 0; ptNum < sampleColsLi.size(); ptNum++)
	{
		std::map<int, std::vector<double> > &pointCols = sampleColsLi[ptNum];
		if(pointCols.size() < 2) continue;
		std::map<int, std::vector<double> >::iterator fit = pointCols.find(currentCam);
		if(fit == pointCols.end()) continue; //Active camera not present
		currentCamGreyLi.push_back(VecRgbToGrey(fit->second));		

		//For the other cameras
		std::vector<double> greyLi;
		for(std::map<int, std::vector<double> >::iterator it = pointCols.begin(); it != pointCols.end(); it++)
		{
			if(it->first == currentCam) continue;
			double grey = VecRgbToGrey(it->second);
			greyLi.push_back(grey * self->camBrightnessLi[it->first]);
		}
		
		double avGrey = VecAverage(greyLi);
		otherCamGreyLi.push_back(avGrey);
	}
	if(currentCamGreyLi.size()==0) throw std::runtime_error("No points");
	if(otherCamGreyLi.size()==0) throw std::runtime_error("No points");

	double camABright = VecAverage(currentCamGreyLi);
	double otherABright = VecAverage(otherCamGreyLi);
	double brRatio = camABright / otherABright; //Active brightness over other brightness
	return brRatio;
}

//**************************************************************************
//http://stackoverflow.com/a/236803

std::vector<std::string> &split(const std::string &s, char delim, std::vector<std::string> &elems) {
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, delim)) {
        elems.push_back(item);
    }
    return elems;
}

std::vector<std::string> split(const std::string &s, char delim) {
    std::vector<std::string> elems;
    split(s, delim, elems);
    return elems;
}

// **********************************************************************

class PxInfo
{
public:
	long camId;
	float x, y;

	PxInfo()
	{
		x = 0;
		y = 0;
	}

	PxInfo(const PxInfo &in)
	{
		PxInfo::operator=(in);
	}	

	const PxInfo &operator=(const PxInfo &in)
	{
		camId = in.camId;
		x = in.x;
		y = in.y;
		return *this;
	}
};

// **********************************************************************

static void PanoView_dealloc(PanoView *self)
{
	if(self->cameraArrangement != NULL)
	{
		Py_DECREF(self->cameraArrangement);
		self->cameraArrangement = NULL;
	}
	
	if(self->outProjection != NULL)
	{
		Py_DECREF(self->outProjection);
		self->outProjection = NULL;
	}

	self->ob_type->tp_free((PyObject *)self);
}

int InitOpengl(PanoView *self)
{	
	int argc = 1; 
	char *arg1 = new char[9];
	strcpy(arg1, "pano.dll");
	char **argv = &arg1;
	if(!gGlutInitDone)
	{
		glutInit(&argc, argv);
		glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH);
		gGlutInitDone = 1;
	}
	glutInitWindowSize(self->outImgW, self->outImgH);

	int glut_id = glutCreateWindow("VWGL");
	int hideOpenGL = 1;
	if(hideOpenGL)
	{
		/*GLuint fbo, renderBuff;
		glGenFramebuffersEXT(1, &fbo);
		glGenRenderbuffers(1, &renderBuff);
		glBindRenderbuffer(fbo);
		glRenderbufferStorage(GL_RENDERBUFFER, GL_BGRA8, outWidth, outHeight);
		glBindFramebuffer(GL_DRAW_FRAMEBUFFER, fbo);*/

		glutHideWindow();
	}

	delete [] arg1;

	glutCloseFunc(GlutWindowCloseEvent);

	glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION);

	glClearColor(0,0,0,0);
	PrintGlErrors("set clear colour");

	glClear(GL_COLOR_BUFFER_BIT);
	PrintGlErrors("clear colour buff");

	glViewport(0, 0, self->outImgW, self->outImgH);
	PrintGlErrors("set viewport");

	std::string extensions = (const char *)glGetString(GL_EXTENSIONS);
	PrintGlErrors("get extensions");
	std::vector<std::string> splitExt = ::split(extensions, ' ');

	if(0) for(unsigned i=0; i< splitExt.size(); i++)
	{
		std::cout << i << ": " << splitExt[i] << std::endl;
	}

	self->nonPowerTwoTexSupported = FindStringInVector("GL_ARB_texture_non_power_of_two", splitExt);

	const GLubyte *ven = glGetString(GL_VENDOR);
	PrintGlErrors("get vendor");
	if(ven!=NULL) std::cout << "opengl vendor: " << ven << std::endl;
	const GLubyte *ren = glGetString(GL_RENDERER);
	PrintGlErrors("get renderer");
	if(ren!=NULL) std::cout << "opengl renderer: " << ren << std::endl;

	return 1;
}

static int PanoView_init(PanoView *self, PyObject *args,
		PyObject *kwargs)
{
	self->dstXRangeSet = 0;
	self->dstYRangeSet = 0;
	self->dstXMin = 0.;
	self->dstXMax = 0.;
	self->dstYMin = 0.;
	self->dstYMax = 0.;
	self->blend = 0;
	self->autoBright = 1;

	if(PyTuple_Size(args) < 2)
	{
		PyErr_Format(PyExc_RuntimeError, "Two arguments required.");
 		return 0;
	}

	PyObject *outProj = PyTuple_GetItem(args, 1);
	if(!PyObject_HasAttrString(outProj, "imgW")||!PyObject_HasAttrString(outProj, "imgH"))
	{
		PyErr_Format(PyExc_RuntimeError, "imgH or imgW not set");
 		return 0;
	}

	//Store objects for later use
	self->cameraArrangement = PyTuple_GetItem(args, 0);
	Py_INCREF(self->cameraArrangement);
	self->outProjection = PyTuple_GetItem(args, 1);
	Py_INCREF(self->outProjection);

	//Store output dimensions
	PyObject *outWidthObj = PyObject_GetAttrString(self->outProjection, "imgW");
	PyObject *outHeightObj = PyObject_GetAttrString(self->outProjection, "imgH");
	long outWidth = PyInt_AsLong(outWidthObj);
	long outHeight = PyInt_AsLong(outHeightObj);
	std::cout << "PanoView_init: " << outWidth << "," << outHeight << std::endl;

	self->outImgW = outWidth;
	self->outImgH = outHeight;
	Py_DECREF(outWidthObj);
	Py_DECREF(outHeightObj);

	InitOpengl(self);

	return 0;
}

static PyObject *PanoView_SetProjection(PanoView *self, PyObject *args,
		PyObject *kwargs)
{
	long oldImgW = self->outImgW;
	long oldImgH = self->outImgH;

	//Remove old projection reference
	if(self->outProjection != NULL)
		Py_DECREF(self->outProjection);
	self->outProjection = NULL;

	//Add new reference
	self->outProjection = PyTuple_GetItem(args, 0);
	Py_INCREF(self->outProjection);	

	//Store output dimensions
	PyObject *outWidthObj = PyObject_GetAttrString(self->outProjection, "imgW");
	PyObject *outHeightObj = PyObject_GetAttrString(self->outProjection, "imgH");
	PyObject *cLatObj = PyObject_GetAttrString(self->outProjection, "cLat");
	PyObject *cLonObj = PyObject_GetAttrString(self->outProjection, "cLon");
	long outWidth = PyInt_AsLong(outWidthObj);
	long outHeight = PyInt_AsLong(outHeightObj);
	double cLat = PyFloat_AsDouble(cLatObj);
	double cLon = PyFloat_AsDouble(cLonObj);
	//std::cout << "PanoView_SetProjection: " << outWidth << "," << outHeight << std::endl;
	//std::cout << cLat << "," << cLon << std::endl;

	self->outImgW = outWidth;
	self->outImgH = outHeight;
	Py_DECREF(outWidthObj);
	Py_DECREF(outHeightObj);
	Py_DECREF(cLatObj);
	Py_DECREF(cLonObj);

	//Clear old display lists
	for(unsigned int i=0; i< self->displayLists.size(); i++)
		glDeleteLists(self->displayLists[i], 1);
	self->displayLists.clear();
	self->displayListImgWidth.clear();
	self->displayListImgHeight.clear();

	//Clear auto exposure sample points
	self->samplePoints.clear();

	if(self->outImgW != oldImgW || self->outImgH != oldImgH)
		InitOpengl(self);

	Py_RETURN_NONE;
}

static PyObject *PanoView_ClearTextures(PanoView *self)
{
	self->srcImgRawLi.clear();
	self->srcImgRawLenLi.clear();
	self->srcHeightLi.clear();
	self->srcWidthLi.clear();
	self->srcFmtLi.clear();

	//Free python structures
	for(unsigned i=0;i < self->srcPyImage.size(); i++)
		Py_DECREF(self->srcPyImage[i]);
	self->srcPyImage.clear();
	for(unsigned i=0;i < self->srcMetaObj.size(); i++)
		Py_DECREF(self->srcMetaObj[i]);
	self->srcMetaObj.clear();

	Py_RETURN_NONE;
}

static PyObject *PanoView_LoadTextures(PanoView *self, PyObject *args)
{

	if(PyTuple_Size(args) < 2)
	{
		PyErr_Format(PyExc_RuntimeError, "Two arguments required.");
 		return NULL;
	}

	//double startTime = double(clock()) / CLOCKS_PER_SEC;
	PyObject *images = PyTuple_GetItem(args, 0);
	PyObject *metas = PyTuple_GetItem(args, 1);
	
	Py_ssize_t numSources = PySequence_Size(images);
	Py_ssize_t numMetas = PySequence_Size(metas);
	if(numSources != numMetas)
	{
		PyErr_Format(PyExc_RuntimeError, "Number of sources and metas must match.");
 		return NULL;
	}

	//Prepare to iterate over cameras in arrangement
	PyObject *addedPhotos = PyObject_GetAttrString(self->cameraArrangement, "addedPhotos");
	if(addedPhotos==NULL) throw std::runtime_error("addedPhotos pointer is null");
	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	if(addedPhotosItems==NULL) throw std::runtime_error("addedPhotosItems pointer is null");
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	// ***************************************************
	// Load source images from python structures
	// ***************************************************

	PanoView_ClearTextures(self);

	for(Py_ssize_t i=0; i<numCams; i++)
	{
		//Get meta data from python objects
		PyObject *pyImage = PySequence_GetItem(images, i);
		if(pyImage==NULL) throw std::runtime_error("pyImage pointer is null");
		PyObject *metaObj = PySequence_GetItem(metas, i);
		if(metaObj==NULL) throw std::runtime_error("metaObj pointer is null");

		if(pyImage == Py_None || metaObj == Py_None)
		{
			self->srcImgRawLi.push_back(NULL);
			self->srcImgRawLenLi.push_back(0);
			self->srcHeightLi.push_back(0);
			self->srcWidthLi.push_back(0);
			self->srcFmtLi.push_back("NULL");
			self->srcPyImage.push_back(NULL);
			self->srcMetaObj.push_back(NULL);
			Py_DECREF(pyImage);
			Py_DECREF(metaObj);
			continue;
		}

		PyObject *widthObj = PyDict_GetItemString(metaObj, "width");
		if(widthObj==NULL) throw std::runtime_error("widthObj pointer is null");
		long sourceWidth = PyInt_AsLong(widthObj);
		PyObject *heightObj = PyDict_GetItemString(metaObj, "height");
		if(heightObj==NULL) throw std::runtime_error("heightObj pointer is null");
		long sourceHeight = PyInt_AsLong(heightObj);

		PyObject *formatObj = PyDict_GetItemString(metaObj, "format");
		std::string sourceFmt = PyString_AsString(formatObj);

		char *imgRaw = PyByteArray_AsString(pyImage);
		if(imgRaw==NULL) throw std::runtime_error("imgRaw pointer is null");
		self->srcImgRawLi.push_back(imgRaw);
		self->srcImgRawLenLi.push_back(PyByteArray_Size(pyImage));
		self->srcHeightLi.push_back(sourceHeight);
		self->srcWidthLi.push_back(sourceWidth);
		self->srcFmtLi.push_back(sourceFmt);
		Py_INCREF(metaObj);
		self->srcPyImage.push_back(pyImage);
		Py_INCREF(pyImage);
		self->srcMetaObj.push_back(metaObj);

		Py_DECREF(pyImage);
		Py_DECREF(metaObj);
	}

	Py_DECREF(addedPhotos);
	Py_DECREF(addedPhotosItems);

	Py_RETURN_NONE;
}

static PyObject *PanoView_CopyTexturesToOpenGL(PanoView *self)
{
	//Prepare to iterate over cameras in arrangement
	PyObject *addedPhotos = PyObject_GetAttrString(self->cameraArrangement, "addedPhotos");
	if(addedPhotos==NULL) throw std::runtime_error("addedPhotos pointer is null");
	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	if(addedPhotosItems==NULL) throw std::runtime_error("addedPhotosItems pointer is null");
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	if(self->openglTxWidthLi.size() > numCams) self->openglTxWidthLi.clear();
	while(self->openglTxWidthLi.size() < numCams) self->openglTxWidthLi.push_back(0);
	if(self->openglTxHeightLi.size() > numCams) self->openglTxHeightLi.clear();
	while(self->openglTxHeightLi.size() < numCams) self->openglTxHeightLi.push_back(0);

	// ***************************************************
	// Copy textures to OpenGL
	// ***************************************************

	while(self->textureIds.size() < numCams)
	{
		//Get texture handle
		GLuint texture;
		glGenTextures(1, &texture);
		PrintGlErrors("allocate a texture");
		std::cout << "allocate texture " << texture << std::endl;
		self->textureIds.push_back(texture);
	}

	//Load textures into opengl
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		glEnable(GL_TEXTURE_2D);
		if(self->blend)
		{
			glEnable(GL_BLEND);
			glBlendFunc(GL_ONE_MINUS_DST_ALPHA, GL_DST_ALPHA);
			PrintGlErrors("set blend mode");
		}
		else
		{
			glDisable(GL_BLEND);
			PrintGlErrors("disable blending");
		}
		//glBlendEquation(GL_FUNC_ADD);

		glBindTexture(GL_TEXTURE_2D, self->textureIds[i]);
		if(self->nonPowerTwoTexSupported)
		{
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self->srcWidthLi[i], 
				self->srcHeightLi[i], 0, GL_RGB, GL_UNSIGNED_BYTE, self->srcImgRawLi[i]);
			self->openglTxWidthLi[i] = self->srcWidthLi[i];
			self->openglTxHeightLi[i] = self->srcHeightLi[i];

			PrintGlErrors("transfer tex");
			//std::cout << i << "\t" << sourceWidth[i] << "," << srcHeightLi[i] << std::endl;
		}
		else
		{
			//Convert to powers of two shape
			unsigned char *openglTex = NULL;
			unsigned openglTexLen = 0, openglTxWidth = 0, openglTxHeight = 0;

			int texOk = ResizeToPowersOfTwo((unsigned char *)self->srcImgRawLi[i], 
				self->srcWidthLi[i], self->srcHeightLi[i], 
				self->srcFmtLi[i].c_str(), &openglTex, &openglTexLen,
				&openglTxWidth, &openglTxHeight);
			self->openglTxWidthLi[i] = openglTxWidth;
			self->openglTxHeightLi[i] = openglTxHeight;

			if(openglTex!=NULL)
			{
				if(texOk)
				{
					//Load texture into opengl
					glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, openglTxWidth, 
						openglTxHeight, 0, GL_RGB, GL_UNSIGNED_BYTE, openglTex);

					PrintGlErrors("transfer tex2");
				}
				delete [] openglTex;
				openglTex = NULL;
			}
		}

		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		PrintGlErrors("set texture params");

	}

	Py_DECREF(addedPhotos);
	Py_DECREF(addedPhotosItems);

	Py_RETURN_NONE;
}

static PyObject *PanoView_CalcAutoExposure(PanoView *self)
{
	//Prepare to iterate over cameras in arrangement
	PyObject *addedPhotos = PyObject_GetAttrString(self->cameraArrangement, "addedPhotos");
	if(addedPhotos==NULL) throw std::runtime_error("addedPhotos pointer is null");
	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	if(addedPhotosItems==NULL) throw std::runtime_error("addedPhotosItems pointer is null");
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	if(self->camBrightnessLi.size() > numCams) self->camBrightnessLi.clear();
	while(self->camBrightnessLi.size() < numCams) self->camBrightnessLi.push_back(1.);

	// ***************************************************
	// Automatic Exposure Control
	// ***************************************************

	if(self->autoBright)
	{
	int nsamp = 50;

	//Check the sample structure is correct size, if not reinitialise it
	int regenSampleMapping = 0;
	if(self->samplePoints.size() != nsamp*nsamp)
	{
		self->samplePoints.clear();
		regenSampleMapping = 1;
	}
	while(self->samplePoints.size() < nsamp*nsamp)
	{
		std::map<int, std::vector<double> > tmp;
		self->samplePoints.push_back(tmp);
		regenSampleMapping = 1;
	}

	//Iterate over cameras and find where the sample points are in the source image
	if(regenSampleMapping)
	{
		//Find points that are common in images
		PyObject *samplePxPos = PyList_New(0);
		for(int x = 0; x < nsamp; x++)
		for(int y = 0; y < nsamp; y++)
		{
			double px = (double)x * (double)self->outImgW / (double)nsamp;
			double py = (double)y * (double)self->outImgH / (double)nsamp;
			PyObject *tupleTemp = PyTuple_New(2);
			PyTuple_SetItem(tupleTemp, 0, PyFloat_FromDouble(px));
			PyTuple_SetItem(tupleTemp, 1, PyFloat_FromDouble(py));
			PyList_Append(samplePxPos, tupleTemp);
			Py_DECREF(tupleTemp);
			//std::cout << x << "," << y << "," << px << "," << py << std::endl;
		}
		Py_ssize_t numSamplePoints = PySequence_Size(samplePxPos);

		//TODO what about wrap around effects in this case of sampling?

		//Transform sample points to lat lon
		PyObject *pxToLatLonUnProj = PyObject_GetAttrString(self->outProjection, "UnProj");
		if(pxToLatLonUnProj==NULL)
			throw std::runtime_error("UnProj method not defined");
	
		PyObject *unprojArgs = PyTuple_New(1);
		PyTuple_SetItem(unprojArgs, 0, samplePxPos);
		PyObject *sampleLatLons = PyObject_Call(pxToLatLonUnProj, unprojArgs, NULL);
		//PyObject_Print(sampleLatLons,stdout,Py_PRINT_RAW); printf("\n");

		Py_DECREF(unprojArgs);
		Py_DECREF(pxToLatLonUnProj);
		Py_DECREF(samplePxPos);

		for(Py_ssize_t i=0; i<numCams; i++)
		{
			//Get camera projection function
			PyObject *camDataTup = PySequence_GetItem(addedPhotosItems, i);
			PyObject *camIdObj = PyTuple_GetItem(camDataTup, 0);
			long camId = PyLong_AsLong(camIdObj);
			PyObject *camData = PyTuple_GetItem(camDataTup, 1);

			//Transform world lat lon to source image
			PyObject *camProj = PyObject_GetAttrString(camData, "Proj");
			if(camProj==NULL)
				throw std::runtime_error("Proj method not defined");

			PyObject *unprojArgs = PyTuple_New(1);
			PyTuple_SetItem(unprojArgs, 0, sampleLatLons);
			Py_INCREF(sampleLatLons);
		
			PyObject *sourceSamplePos = PyObject_Call(camProj, unprojArgs, NULL);
		
			Py_DECREF(unprojArgs);
			Py_DECREF(camProj);

			Py_ssize_t numRetPoints = PySequence_Size(sourceSamplePos);

			//std::cout << "Cam sample points: " << i << "," << numRetPoints << std::endl;
			//std::cout.flush();

			for(Py_ssize_t ptNum = 0; ptNum < numRetPoints; ptNum++)
			{
				PyObject *retPtTup = PySequence_GetItem(sourceSamplePos, ptNum);
				PyObject *xObj = PySequence_GetItem(retPtTup, 0);
				PyObject *yObj = PySequence_GetItem(retPtTup, 1);
				PyObject *ptTest = PySequence_GetItem(sampleLatLons, ptNum);

				if(xObj != Py_None)
				{
					std::map<int, std::vector<double> > &samplePoint = self->samplePoints[ptNum];
					std::vector<double> pt;
					pt.push_back(PyFloat_AsDouble(xObj));
					pt.push_back(PyFloat_AsDouble(yObj));
					samplePoint[i] = pt;

					//PyObject_Print(retPtTup,stdout,Py_PRINT_RAW);
					//PyObject_Print(ptTest,stdout,Py_PRINT_RAW); printf("\n");
				}

				Py_DECREF(xObj);
				Py_DECREF(yObj);
				Py_DECREF(retPtTup);
				Py_DECREF(ptTest);
			}

			//PyObject_Print(sourceSamplePos,stdout,Py_PRINT_RAW); printf("\n");

			Py_DECREF(sourceSamplePos);
			Py_DECREF(camDataTup);
		}

		Py_DECREF(sampleLatLons);
	}

	//For each sample point in auto exposure calc, store colour
	std::vector<std::map<int, std::vector<double> > > sampleColsLi;
	for(unsigned ptNum = 0; ptNum < self->samplePoints.size(); ptNum++)
	{
		std::map<int, std::vector<double> > &samplePoint = self->samplePoints[ptNum];
		std::map<int, std::vector<double> > sampleCols;
		if(samplePoint.size() < 2) continue;

		//For each camera
		for(std::map<int, std::vector<double> >::iterator it = samplePoint.begin(); it != samplePoint.end(); it++)
		{
			//Get the pixel colour in the source texture
			int camNum = it->first;
			double px = it->second[0];
			double py = it->second[1];
			//std::cout << ptNum << "," << camNum << "," << px << "," << py << std::endl;
			std::vector<double> pix;
			try
			{
				char *rawImg = PyByteArray_AsString(self->srcPyImage[camNum]);
				unsigned rawImgLen = PyByteArray_Size(self->srcPyImage[camNum]);

				pix = GetPixFromRawBuff((const unsigned char*)rawImg, 
					rawImgLen, self->srcWidthLi[camNum], 
					self->srcHeightLi[camNum], px, py, self->srcFmtLi[camNum].c_str());
			}
			catch(std::runtime_error)
			{
				
			}
			if (pix.size() >= 3)
			{
				//std::cout << pix[0] << "," << pix[1] << "," << pix[2] << std::endl;
				std::vector<double> col;
				col.push_back(pix[0]);
				col.push_back(pix[1]);
				col.push_back(pix[2]);
				sampleCols[camNum] = col;
			}
		}

		sampleColsLi.push_back(sampleCols);
	}

	//Scale brightness of cameras
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		try
		{
			double brRatio = CompareCameraBrightness(i, self, sampleColsLi);
			//std::cout << i << " brRatio " << brRatio << std::endl;
			self->camBrightnessLi[i] = 1./brRatio;
		}
		catch(std::runtime_error &err)
		{
			//std::cout << "Error:" << err.what() << std::endl;
		}
	}

	//Normalise brightness so max brightness is one
	double maxBright = 0.;
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		if(self->camBrightnessLi[i] > maxBright)
			maxBright = self->camBrightnessLi[i];
	}	
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		self->camBrightnessLi[i] /= maxBright;
		//std::cout << i << " brightness " << self->camBrightnessLi[i] << std::endl;
	}
	}
	else
	{
		//Auto brightness is disabled
		self->samplePoints.clear();

		for(Py_ssize_t i=0; i<numCams; i++)
		{	
			self->camBrightnessLi[i] = 1.;
		}
	}

	Py_DECREF(addedPhotos);
	Py_DECREF(addedPhotosItems);

	Py_RETURN_NONE;
}

static PyObject *PanoView_Vis(PanoView *self, PyObject *args)
{
	//Prepare to iterate over cameras in arrangement
	PyObject *addedPhotos = PyObject_GetAttrString(self->cameraArrangement, "addedPhotos");
	if(addedPhotos==NULL) throw std::runtime_error("addedPhotos pointer is null");
	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	if(addedPhotosItems==NULL) throw std::runtime_error("addedPhotosItems pointer is null");
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	if(self->camBrightnessLi.size() > numCams) self->camBrightnessLi.clear();
	while(self->camBrightnessLi.size() < numCams) self->camBrightnessLi.push_back(1.);

	//Create output image buffer
	unsigned pxOutSize = 3 * self->outImgH * self->outImgW;
	PyObject *pxOut = PyByteArray_FromStringAndSize("", 0);
	PyByteArray_Resize(pxOut, pxOutSize);
	char *pxOutRaw = PyByteArray_AsString(pxOut);

	//Initialize output image colour
	memset(pxOutRaw, 0x00, pxOutSize);

	glClear(GL_COLOR_BUFFER_BIT);
	PrintGlErrors("clear colour buff");

	// ***************************************************
	// Draw images to display lists
	// ***************************************************

	//Initialise memory to contain display lists
	while(self->displayLists.size() < numCams)
		self->displayLists.push_back(0);
	while(self->displayListImgWidth.size() < numCams)
		self->displayListImgWidth.push_back(0);
	while(self->displayListImgHeight.size() < numCams)
		self->displayListImgHeight.push_back(0);

	//Create display lists of camera lens shapes
	for(Py_ssize_t i=0; i<numCams; i++)
	{

		long sourceWidth = self->srcWidthLi[i];
		long sourceHeight = self->srcHeightLi[i];

		//std::cout << i<<"src " << sourceWidth << "," << sourceHeight << std::endl;
		//std::cout << i<<"expected " << self->displayListImgWidth[i] << "," << self->displayListImgHeight[i] << std::endl;

		//If input image has an unexpected size for the corresponding display list,
		//delete and regenerate the display list
		if(self->displayLists[i] != 0  && (sourceWidth != self->displayListImgWidth[i]
			|| sourceHeight != self->displayListImgHeight[i]))
		{
			std::cout << "Deleting display list "<< self->displayLists[i] << std::endl;
			glDeleteLists(self->displayLists[i], 1);
			self->displayLists[i] = 0;
		}
		
		//std::cout << i << "\t" << self->displayLists[i] << std::endl;

		//Existing display list is fine, continue
		if(self->displayLists[i] != 0)
			continue;

		GLuint dl = glGenLists(1);
		PrintGlErrors("create display list");

		glNewList(dl,GL_COMPILE);
		PrintGlErrors("compile display list");

		std::cout << "Generating display list " << dl << " for cam " << i << std::endl;
		std::cout.flush();

		//Check positions in source image of world positions
		PyObject *camDataTup = PySequence_GetItem(addedPhotosItems, i);
		PyObject *camIdObj = PyTuple_GetItem(camDataTup, 0);
		long camId = PyLong_AsLong(camIdObj);
		PyObject *camData = PyTuple_GetItem(camDataTup, 1);

		//Generate python list of source image positions
		PyObject *imgPix = PyList_New(0);
		std::vector<std::vector<double> > texPos;
		const int numSq = 20;

		for(int xstep = 0; xstep < numSq; xstep ++)
		{
			for(int ystep = 0; ystep < numSq; ystep ++)
			{
				//Store image position
				double x = sourceWidth * double(xstep) / (numSq-1.);
				double y = sourceHeight * double(ystep) / (numSq-1.);

				PyObject *tupleTemp = PyTuple_New(2);
				PyTuple_SetItem(tupleTemp, 0, PyInt_FromLong(x));
				PyTuple_SetItem(tupleTemp, 1, PyInt_FromLong(y));
				PyList_Append(imgPix, tupleTemp);
				Py_DECREF(tupleTemp);

				//Store normalised texture position
				std::vector<double> txPt;
				txPt.push_back(x / self->openglTxWidthLi[i]);
				txPt.push_back(y / self->openglTxHeightLi[i]);
				texPos.push_back(txPt);
			}
		}

		//Generate indices for complete squares
		std::vector<std::vector<int> > sqInd;
		std::vector<double> sqIndAlpha;
		for(int x = 0; x < numSq-1; x ++)
		{
			double hwidth = ((double)numSq-1.) / 2.;
			double xmid = 1. - fabs(((double)x - hwidth) / hwidth);

			for(int y = 0; y < numSq-1; y ++)
			{
				double ymid = 1. - fabs(((double)y - hwidth) / hwidth);
	
				std::vector<int> singleSq;
				singleSq.push_back(x + y * numSq);
				singleSq.push_back((x + 1) + y * numSq);
				singleSq.push_back((x + 1) + (y + 1) * numSq);
				singleSq.push_back(x + (y + 1) * numSq);
				sqInd.push_back(singleSq);

				sqIndAlpha.push_back(xmid * ymid);
			}
		}

		//Transfrom image source positions to world coordinates
		PyObject *camUnProj = PyObject_GetAttrString(camData, "UnProj");
		if(camUnProj==NULL)
			throw std::runtime_error("UnProj method not defined");

		//PyObject_Print(camUnProj,stdout,Py_PRINT_RAW); printf("\n");

		PyObject *unprojArgs = PyTuple_New(1);
		PyTuple_SetItem(unprojArgs, 0, imgPix);
		//Py_INCREF(imgPix);

		PyObject *worldPos = PyObject_Call(camUnProj, unprojArgs, NULL);
		//PyObject_Print(worldPos, stdout, Py_PRINT_RAW); std::cout << std::endl;
		Py_DECREF(camUnProj);

		//Transform world positions to destination image
		PyObject *dstProj = PyObject_GetAttrString(self->outProjection, "MultiProj");
		if(dstProj==NULL)
			throw std::runtime_error("MultiProj method not defined");

		PyObject *projArgs = PyTuple_New(1);
		PyTuple_SetItem(projArgs, 0, worldPos);
		//Py_INCREF(worldPos);

		//PyObject_Print(dstProj,stdout,Py_PRINT_RAW); printf("\n");

		PyObject *dstPos = PyObject_Call(dstProj, projArgs, NULL);
		Py_DECREF(dstProj);

		//PyObject_Print(dstPos,stdout,Py_PRINT_RAW); printf("\n");

		//Draw images using opengl to display lists
		if(self->textureIds[i] >= 0)
			glBindTexture(GL_TEXTURE_2D, self->textureIds[i]);
		glColor3d(self->camBrightnessLi[i],self->camBrightnessLi[i],self->camBrightnessLi[i]);

		//For each square in piecewise grid		
		for(unsigned sqNum = 0; sqNum < sqInd.size(); sqNum++)
		{
			std::vector<int> &singleSq = sqInd[sqNum];
			double alpha = sqIndAlpha[sqNum];

			//Check how many valid destination positions were found
			PyObject *dstPtLi = PySequence_GetItem(dstPos, singleSq[0]);
			Py_ssize_t numDestPoints = PySequence_Size(dstPtLi);
			Py_DECREF(dstPtLi);

			//The projection mapping is one to many
			//Iterate over destination points
			for(Py_ssize_t destNum = 0; destNum < numDestPoints; destNum++)
			{

			std::vector<double> ptx, pty, texx, texy, alphaLi;
			int isValid = 1;
			//Check each corner point and see if any are None valued
			for(Py_ssize_t c = 0; c < singleSq.size(); c++)
			{
				int ptInd = singleSq[c];
				PyObject *dstLi = PySequence_GetItem(dstPos, ptInd);
				PyObject *dstPt = PySequence_GetItem(dstLi, destNum);
				//std::cout << singleSq[c] << ",";

				if(PySequence_Size(dstPt)< 2)
				{
					isValid = 0;
					continue;
				}
				PyObject *pydstx = PySequence_GetItem(dstPt, 0);
				PyObject *pydsty = PySequence_GetItem(dstPt, 1);
				if (pydstx == Py_None)
					isValid = 0;
				else
				{
					double dstx = PyFloat_AsDouble(pydstx);
					ptx.push_back(dstx);
				}

				if (pydsty == Py_None)
					isValid = 0;
				else
				{
					double dsty = PyFloat_AsDouble(pydsty);
					pty.push_back(dsty);
				}

				//std::cout << "tex " << texPos[ptInd][0] <<","<< texPos[ptInd][1] << std::endl;
				//std::cout << "pt " << c << "," << (dstx / self->outImgW) <<","<< (dsty / self->outImgH) << std::endl;
				texx.push_back(texPos[ptInd][0]);
				texy.push_back(texPos[ptInd][1]);
				alphaLi.push_back(alpha);

				Py_DECREF(pydstx);
				Py_DECREF(pydsty);
				Py_DECREF(dstPt);
				Py_DECREF(dstLi);
			}

			if(!isValid)
				continue; //Skip this invalid square

			glBegin(GL_QUADS);
			//For each corner of the square
			for(int c = 0; c < ptx.size(); c++)
			{
				int ptInd = singleSq[c];

				glTexCoord2d(texx[c],texy[c]);
				glColor4d(1., 1., 1., alphaLi[c]);
				glVertex2f(ptx[c],pty[c]);
			}
			//std::cout << std::endl;
			glEnd();
			}


		}

		Py_DECREF(dstProj);
		Py_DECREF(worldPos);
		Py_DECREF(unprojArgs);
		Py_DECREF(imgPix);
		Py_DECREF(camDataTup);

		glEndList();
		PrintGlErrors("end display list");
		self->displayLists[i] = dl;
		self->displayListImgWidth[i] = sourceWidth;
		self->displayListImgHeight[i] = sourceHeight;
	}

	// ***************************************************
	// Automatic Scaling
	// ***************************************************

	//Limit display area to bounds
	if(self->dstXMax > self->outImgW) self->dstXMax = self->outImgW;
	if(self->dstXMin < 0.) self->dstXMin = 0.;
	if(self->dstYMax > self->outImgH) self->dstYMax = self->outImgH;
	if(self->dstYMin < 0.) self->dstYMin = 0.;

	//Scale display area to fit
	glLoadIdentity();
	int showEntire = 1;
	if(showEntire || !self->dstXRangeSet)
	{
		glTranslated(-1.0, -1.0, 0.);
		//std::cout << "x" << self->outImgW << "," << self->outImgH << std::endl;
		glScaled(2./self->outImgW, 2./self->outImgH, 1.);
	}
	else
	{
		//Determine area to show
		double xrange = self->dstXMax - self->dstXMin;
		double yrange = self->dstYMax - self->dstYMin;
		double avx = 0.5*(self->dstXMax + self->dstXMin);
		double avy = 0.5*(self->dstYMax + self->dstYMin);

		double aspectRatio = self->outImgW / self->outImgH;

		//Check if we are too wide for aspect
		double maxWidth = yrange / aspectRatio;
		if(maxWidth > xrange) xrange = maxWidth;

		//Check if we are too tall for aspect
		double maxHeight = xrange * aspectRatio;
		if(maxHeight > yrange) yrange = maxHeight;

		glScaled(2./xrange, 2./yrange, 1.);
		glTranslated(-avx, -avy, 0.);
	}
	PrintGlErrors("scale view");
	
	// ***************************************************
	// Draw images
	// ***************************************************

	//Perform actual drawing from display lists
	for(int i=0;i< self->displayLists.size(); i++)
	{
		if(self->displayLists[i] == 0)
			continue;

		//Draw centre image
		glPushMatrix();
		glCallList(self->displayLists[i]);
		glPopMatrix();
	}
	PrintGlErrors("draw display list");

	/*for(int i=0;i<self->textureIds.size(); i++)
	{
		//Delete opengl texture
		if(self->textureIds[i] >= 0)
			glDeleteTextures(1, &self->textureIds[i]);
	}
	self->textureIds.clear();
	PrintGlErrors("clear old textures");*/

	glReadBuffer(GL_BACK);
	glReadPixels(0,0,self->outImgW,self->outImgH,GL_RGB,GL_UNSIGNED_BYTE,pxOutRaw);
	PrintGlErrors("read back buffer");

	glutSwapBuffers();

	//Format meta data
	PyObject *metaOut = PyDict_New();
	PyObject *widthObj = PyInt_FromLong(self->outImgW);
	PyObject *heightObj = PyInt_FromLong(self->outImgH);
	PyObject *formatObj = PyString_FromString("RGB24");
	PyDict_SetItemString(metaOut, "width", widthObj);
	PyDict_SetItemString(metaOut, "height", heightObj);
	PyDict_SetItemString(metaOut, "format", formatObj);
	Py_DECREF(widthObj);
	Py_DECREF(heightObj);
	Py_DECREF(formatObj);

	PyObject *out = PyTuple_New(2);
	PyTuple_SetItem(out, 0, pxOut);
	PyTuple_SetItem(out, 1, metaOut);

	//double endTime = double(clock()) / CLOCKS_PER_SEC;
	//std::cout << "PanoView_Vis " << endTime - startTime << std::endl;

	Py_DECREF(addedPhotos);
	Py_DECREF(addedPhotosItems);

	//Py_RETURN_NONE;
	return out;
}

static PyObject *PanoView_SetSmoothBlending(PanoView *self, PyObject *args)
{
	if(PyTuple_Size(args) < 1)
	{
		PyErr_Format(PyExc_RuntimeError, "One argument required.");
 		Py_RETURN_NONE;
	}

	self->blend = 1;
	PyObject *blendObj = PyTuple_GetItem(args, 0);
	if(blendObj == Py_False) self->blend = 0;
	
	Py_RETURN_NONE;
}

static PyObject *PanoView_SetAutoBright(PanoView *self, PyObject *args)
{
	if(PyTuple_Size(args) < 1)
	{
		PyErr_Format(PyExc_RuntimeError, "One argument required.");
 		Py_RETURN_NONE;
	}

	self->autoBright = 1;
	PyObject *blendObj = PyTuple_GetItem(args, 0);
	if(blendObj == Py_False) self->autoBright = 0;
	
	Py_RETURN_NONE;
}


// *********************************************************************

static PyMethodDef PanoView_methods[] = {
	{"Vis", (PyCFunction)PanoView_Vis, METH_VARARGS,
			 "Vis()\n\n"
			 "Combine images to form a panorama"},
	{"SetProjection", (PyCFunction)PanoView_SetProjection, METH_VARARGS,
			 "SetProjection(outProjection)\n\n"
			 "Update the projection used for output"},
	{"SetSmoothBlending", (PyCFunction)PanoView_SetSmoothBlending, METH_VARARGS,
			 "SetSmoothBlending(enabled)\n\n"
			 "Enable or disable smooth blending"},
	{"SetAutoBright", (PyCFunction)PanoView_SetAutoBright, METH_VARARGS,
			 "SetAutoBright(enabled)\n\n"
			 "Enable or disable auto brightness"},
	{"LoadTextures", (PyCFunction)PanoView_LoadTextures, METH_VARARGS,
			 "LoadTextures(image_byte_buffer_list, meta_data_list)\n\n"
			 "Set textures for visualisation."},
	{"ClearTextures", (PyCFunction)PanoView_ClearTextures, METH_NOARGS,
			 "ClearTextures()\n\n"
			 "Clear stored textures."},
	{"CopyTexturesToOpenGL", (PyCFunction)PanoView_CopyTexturesToOpenGL, METH_NOARGS,
			 "CopyTexturesToOpenGL()\n\n"
			 "Copy textures to opengl."},
	{"CalcAutoExposure", (PyCFunction)PanoView_CalcAutoExposure, METH_NOARGS,
			 "CalcAutoExposure()\n\n"
			 "Calculate brightness corrections."},
			 

	{NULL}
};

static PyTypeObject PanoView_type = {
	PyObject_HEAD_INIT(NULL)
			0, "pano.PanoView", sizeof(PanoView), 0,
			(destructor)PanoView_dealloc, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
			0, Py_TPFLAGS_DEFAULT, "PanoView(cameraArrangement, outProjection)\n\n", 0, 0, 0,
			0, 0, 0, PanoView_methods, 0, 0, 0, 0, 0, 0, 0,
			(initproc)PanoView_init
};

// *********************************************************************

static PyMethodDef module_methods[] = {
	{ "testfunc", (PyCFunction)TestFunc, METH_VARARGS, NULL },
	{ NULL, NULL, 0, NULL }
};

PyMODINIT_FUNC initpano(void)
{
	gGlutInitDone = 0;

	PanoView_type.tp_new = PyType_GenericNew;

	if(PyType_Ready(&PanoView_type) < 0)
		{
			return;
		}

	PyObject *module = Py_InitModule3("pano", module_methods,
			"pano tools.");

	if(!module)
		{
			return;
		}

	Py_INCREF(&PanoView_type);
	PyModule_AddObject(module, "PanoView", (PyObject *)&PanoView_type);

}
