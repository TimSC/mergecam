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
};
typedef PanoView_cl PanoView;

static PyObject *TestFunc(PyObject *self, PyObject *args)
{
	Py_RETURN_NONE;
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

	int roundWidth = pow(2, (int)ceil(log2(sourceWidth)));
	int roundHeight = pow(2, (int)ceil(log2(sourceHeight)));
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

void PrintGlErrors()
{	
	GLenum err = glGetError();
	while(err!=GL_NO_ERROR)
	{
		std::cout << "opengl error: " << gluErrorString(err) << std::endl;
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
		int hit = haystack[i].compare(needle);
		if(hit) return true;
	}
	return false;
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

static int PanoView_init(PanoView *self, PyObject *args,
		PyObject *kwargs)
{
	self->dstXRangeSet = 0;
	self->dstYRangeSet = 0;
	self->dstXMin = 0.;
	self->dstXMax = 0.;
	self->dstYMin = 0.;
	self->dstYMax = 0.;

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

	PyObject *outWidthObj = PyObject_GetAttrString(outProj, "imgW");
	PyObject *outHeightObj = PyObject_GetAttrString(outProj, "imgH");
	long outWidth = PyInt_AsLong(outWidthObj);
	long outHeight = PyInt_AsLong(outHeightObj);
	self->outImgW = outWidth;
	self->outImgH = outHeight;
	Py_DECREF(outWidthObj);
	Py_DECREF(outHeightObj);
	
	int argc = 1; 
	char *arg1 = new char[9];
	strcpy(arg1, "pano.dll");
	char **argv = &arg1;
	if(!gGlutInitDone)
	{
		glutInit(&argc, argv);
		glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH);
		glutInitWindowSize(outWidth, outHeight);
		gGlutInitDone = 1;
	}
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
	glClear(GL_COLOR_BUFFER_BIT);

	std::string extensions = (const char *)glGetString(GL_EXTENSIONS);
	std::vector<std::string> splitExt = ::split(extensions, ' ');

	self->nonPowerTwoTexSupported = FindStringInVector("GL_ARB_texture_non_power_of_two", splitExt);

	return 0;
}

void UpdateRanges(PanoView *self, double dstx, double dsty)
{
	//Update ranges
	if(!self->dstXRangeSet)
	{
		self->dstXMin = dstx;
		self->dstXMax = dstx;
		self->dstXRangeSet = 1;
	}
	else
	{
		if(dstx < self->dstXMin) self->dstXMin = dstx;
		if(dstx > self->dstXMax) self->dstXMax = dstx;
	}
		
	if(!self->dstYRangeSet)
	{
		self->dstYMin = dsty;
		self->dstYMax = dsty;
		self->dstYRangeSet = 1;
	}
	else
	{
		if(dsty < self->dstYMin) self->dstYMin = dsty;
		if(dsty > self->dstYMax) self->dstYMax = dsty;
	}
}


static PyObject *PanoView_Vis(PanoView *self, PyObject *args)
{

	if(PyTuple_Size(args) < 2)
	{
		PyErr_Format(PyExc_RuntimeError, "Two arguments required.");
 		Py_RETURN_NONE;
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

	//Create output image buffer
	unsigned pxOutSize = 3 * self->outImgH * self->outImgW;
	PyObject *pxOut = PyByteArray_FromStringAndSize("", 0);
	PyByteArray_Resize(pxOut, pxOutSize);
	char *pxOutRaw = PyByteArray_AsString(pxOut);

	//Initialize output image colour
	memset(pxOutRaw, 0x00, pxOutSize);

	glClear(GL_COLOR_BUFFER_BIT);

	//Iterate over cameras in arrangement
	PyObject *addedPhotos = PyObject_GetAttrString(self->cameraArrangement, "addedPhotos");
	if(addedPhotos==NULL) throw std::runtime_error("addedPhotos pointer is null");
	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	if(addedPhotosItems==NULL) throw std::runtime_error("addedPhotosItems pointer is null");
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	//Load textures into opengl
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		//Get meta data from python objects
		PyObject *pyImage = PySequence_GetItem(images, i);
		if(pyImage==NULL) throw std::runtime_error("pyImage pointer is null");
		PyObject *metaObj = PySequence_GetItem(metas, i);
		if(metaObj==NULL) throw std::runtime_error("metaObj pointer is null");

		if(pyImage == Py_None or metaObj == Py_None)
		{
			self->textureIds.push_back(0);
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

		glEnable(GL_TEXTURE_2D);
		glEnable(GL_BLEND);
		glBlendFunc(GL_ONE_MINUS_DST_ALPHA, GL_DST_ALPHA);
		//glBlendEquation(GL_FUNC_ADD);

		//Get texture handle
		GLuint texture;
		glGenTextures(1, &texture);

		glBindTexture(GL_TEXTURE_2D, texture);
		if(self->nonPowerTwoTexSupported)
		{
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, sourceWidth, 
				sourceHeight, 0, GL_RGB, GL_UNSIGNED_BYTE, imgRaw);
			self->openglTxWidthLi.push_back(sourceWidth);
			self->openglTxHeightLi.push_back(sourceHeight);
		}
		else
		{
			//Convert to powers of two shape
			unsigned char *openglTex = NULL;
			unsigned openglTexLen = 0, openglTxWidth = 0, openglTxHeight = 0;

			int texOk = ResizeToPowersOfTwo((unsigned char *)imgRaw, 
				sourceWidth, sourceHeight, 
				sourceFmt.c_str(), &openglTex, &openglTexLen,
				&openglTxWidth, &openglTxHeight);
			self->openglTxWidthLi.push_back(openglTxWidth);
			self->openglTxHeightLi.push_back(openglTxHeight);

			if(openglTex!=NULL)
			{
				if(texOk)
				{
					//Load texture into opengl
					glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, openglTxWidth, 
						openglTxHeight, 0, GL_RGB, GL_UNSIGNED_BYTE, openglTex);
				}
				delete [] openglTex;
				openglTex = NULL;
			}
		}

		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);

		self->textureIds.push_back(texture);

		Py_DECREF(pyImage);
		Py_DECREF(metaObj);

	}

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

		//Get meta data from python objects
		PyObject *pyImage = PySequence_GetItem(images, i);
		if(pyImage==NULL) throw std::runtime_error("pyImage pointer is null");
		PyObject *metaObj = PySequence_GetItem(metas, i);
		if(metaObj==NULL) throw std::runtime_error("metaObj pointer is null");

		if(pyImage == Py_None or metaObj == Py_None)
		{
			//Skip if camera data is missing
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
		glNewList(dl,GL_COMPILE);
		std::cout << "Generating display list " << dl << std::endl;

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

		PyObject_Print(camUnProj,stdout,Py_PRINT_RAW);

		PyObject *unprojArgs = PyTuple_New(1);
		PyTuple_SetItem(unprojArgs, 0, imgPix);
		//Py_INCREF(imgPix);

		PyObject *worldPos = PyObject_Call(camUnProj, unprojArgs, NULL);
		//PyObject_Print(worldPos, stdout, Py_PRINT_RAW); std::cout << std::endl;

		//Transform world positions to destination image
		PyObject *dstProj = PyObject_GetAttrString(self->outProjection, "Proj");
		if(dstProj==NULL)
			throw std::runtime_error("Proj method not defined");

		PyObject *projArgs = PyTuple_New(1);
		PyTuple_SetItem(projArgs, 0, worldPos);
		//Py_INCREF(worldPos);

		PyObject *dstPos = PyObject_Call(dstProj, projArgs, NULL);

		//Draw images using opengl
		if(self->textureIds[i] >= 0)
			glBindTexture(GL_TEXTURE_2D, self->textureIds[i]);
		glColor3d(1.,1.,1.);
		
		for(unsigned sqNum = 0; sqNum < sqInd.size(); sqNum++)
		{
			std::vector<int> &singleSq = sqInd[sqNum];
			double alpha = sqIndAlpha[sqNum];

			glBegin(GL_QUADS);
			for(int c = 0; c < singleSq.size(); c++)
			{

				int ptInd = singleSq[c];
				PyObject *dstPt = PySequence_GetItem(dstPos, ptInd);
				//std::cout << singleSq[c] << ",";

				if(PySequence_Size(dstPt)< 2) continue;
				PyObject *pydstx = PySequence_GetItem(dstPt, 0);
				PyObject *pydsty = PySequence_GetItem(dstPt, 1);
				double dstx = PyFloat_AsDouble(pydstx);
				double dsty = PyFloat_AsDouble(pydsty);
				//std::cout << "tex " << texPos[ptInd][0] <<","<< texPos[ptInd][1] << std::endl;
				//std::cout << "pt " << c << "," << (dstx / self->outImgW) <<","<< (dsty / self->outImgH) << std::endl;
				glTexCoord2d(texPos[ptInd][0],texPos[ptInd][1]);
				//std::cout << alpha << std::endl;
				glColor4d(1., 1., 1., alpha);
				glVertex2f(dstx,dsty);
				Py_DECREF(dstPt);
				Py_DECREF(pydstx);
				Py_DECREF(pydsty);

				//Update max and min extent but consider wrap around effect
				UpdateRanges(self, dstx, dsty);
				int wrapOutputHorizontally = 1;
				while(dstx > self->outImgW && wrapOutputHorizontally)
				{
					dstx -= self->outImgW;
					UpdateRanges(self, dstx, dsty);
				}

				while(dstx < 0. && wrapOutputHorizontally)
				{
					dstx += self->outImgW;
					UpdateRanges(self, dstx, dsty);
				}
			}
			//std::cout << std::endl;
			glEnd();

		}

		Py_DECREF(dstProj);
		Py_DECREF(worldPos);
		Py_DECREF(unprojArgs);
		Py_DECREF(imgPix);
		Py_DECREF(pyImage);
		Py_DECREF(metaObj);
		Py_DECREF(camDataTup);

		glEndList();
		self->displayLists[i] = dl;
		self->displayListImgWidth[i] = sourceWidth;
		self->displayListImgHeight[i] = sourceHeight;
	}

	//Limit display area to bounds
	if(self->dstXMax > self->outImgW) self->dstXMax = self->outImgW;
	if(self->dstXMin < 0.) self->dstXMin = 0.;
	if(self->dstYMax > self->outImgW) self->dstYMax = self->outImgH;
	if(self->dstYMin < 0.) self->dstYMin = 0.;

	//Scale display area to fit
	glLoadIdentity();
	int showEntire = 0;
	if(showEntire || !self->dstXRangeSet)
	{
		glTranslated(-1.0, -1.0, 0.);
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
	
	//Perform actual drawing
	for(int i=0;i< self->displayLists.size(); i++)
	{
		if(self->displayLists[i] == 0)
			continue;

		glPushMatrix();
		glTranslatef(-self->outImgW,0.,0.);
		glCallList(self->displayLists[i]);
		glPopMatrix();

		glPushMatrix();
		glCallList(self->displayLists[i]);
		glPopMatrix();

		glPushMatrix();
		glTranslatef(self->outImgW,0.,0.);
		glCallList(self->displayLists[i]);
		glPopMatrix();
	}

	for(int i=0;i<self->textureIds.size(); i++)
	{
		//Delete opengl texture
		if(self->textureIds[i] >= 0)
			glDeleteTextures(1, &self->textureIds[i]);
	}
	self->textureIds.clear();

	PrintGlErrors();
	glReadBuffer(GL_BACK);
	glReadPixels(0,0,self->outImgW,self->outImgH,GL_RGB,GL_UNSIGNED_BYTE,pxOutRaw);
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

// *********************************************************************

static PyMethodDef PanoView_methods[] = {
	{"Vis", (PyCFunction)PanoView_Vis, METH_VARARGS,
			 "Vis(image_byte_buffer_list, meta_data_list)\n\n"
			 "Combine images to form a panorama"},
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
