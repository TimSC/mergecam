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

class PanoView_cl{
public:
	PyObject_HEAD

	long outImgW, outImgH;
	PyObject *timeModule;
	PyObject *timeFunc;
	PyObject *cameraArrangement;
	PyObject *outProjection;
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

	/*
	//Create list of screen coordinates
	//std::cout << outWidth << "," << outHeight << std::endl;
	PyObject *imgPix = PyList_New(0);
	for(long x=0;x<outWidth;x++)
	for(long y=0;y<outHeight;y++)
	{
		PyObject *tupleTemp = PyTuple_New(2);
		PyTuple_SetItem(tupleTemp, 0, PyInt_FromLong(x));
		PyTuple_SetItem(tupleTemp, 1, PyInt_FromLong(y));
		PyList_Append(imgPix, tupleTemp);
		Py_DECREF(tupleTemp);		
	}

	//Transform to world coordinates	
	PyObject *outUnProj = PyObject_GetAttrString(outProj, "UnProj");
	if(outUnProj==NULL)
	{
		PyErr_Format(PyExc_RuntimeError, "UnProj method not defined");
		//TODO fix possible memory leaks?
 		return 0;
	}

	PyObject *unProjArgs = PyTuple_New(1);
	PyTuple_SetItem(unProjArgs, 0, imgPix);
	Py_INCREF(imgPix);
	PyObject *worldPix = PyObject_Call(outUnProj, unProjArgs, NULL);

	PyObject *cameraArragement = PyTuple_GetItem(args, 0);
	PyObject *addedPhotos = PyObject_GetAttrString(cameraArragement, "addedPhotos");
	if(addedPhotos==NULL)
	{
		PyErr_Format(PyExc_RuntimeError, "addedPhotos dict not defined");
		//TODO fix possible memory leaks?
 		return 0;
	}

	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	//Initialise low level mapping structure
	std::vector<std::vector<std::vector<class PxInfo> > > &mapping = *self->mapping;
	mapping.clear();
	std::vector<std::vector<class PxInfo> > col;
	for(long y=0;y<outHeight;y++)
	{
		std::vector<class PxInfo> tmp;
		col.push_back(tmp);
	}
	for(long x=0;x<outWidth;x++)
		mapping.push_back(col);

	//Iterate over cameras in arrangement
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		//Check positions in source image of world positions
		PyObject *camDataTup = PySequence_GetItem(addedPhotosItems, i);
		PyObject *camIdObj = PyTuple_GetItem(camDataTup, 0);
		long camId = PyLong_AsLong(camIdObj);
		PyObject *camData = PyTuple_GetItem(camDataTup, 1);

		//PyObject_Print(camData, stdout, Py_PRINT_RAW); std::cout << std::endl;

		PyObject *camProj = PyObject_GetAttrString(camData, "Proj");
		if(camProj==NULL)
		{
			PyErr_Format(PyExc_RuntimeError, "Proj method not defined");
			//TODO fix possible memory leaks?
	 		return 0;
		}

		PyObject *projArgs = PyTuple_New(1);
		PyTuple_SetItem(projArgs, 0, worldPix);
		Py_INCREF(projArgs);

		PyObject *pixMapping = PyObject_Call(camProj, projArgs, NULL);

		//Convert mapping into low level C structure for speed
		if(pixMapping != NULL)
		{
			Py_ssize_t numPix = PySequence_Size(pixMapping);

			if(numPix != PySequence_Size(imgPix))
			{
				PyErr_Format(PyExc_RuntimeError, "Proj function returned unexpected number of points");
				//TODO fix possible memory leaks?
		 		return 0;
			}

			for(Py_ssize_t j=0; j<numPix; j++)
			{
				PyObject *posSrc = PySequence_GetItem(pixMapping, j);
				PyObject *posDst = PySequence_GetItem(imgPix, j);
				//PyObject_Print(posSrc, stdout, Py_PRINT_RAW);
				
				Py_ssize_t numComp = PySequence_Size(posSrc);
				int noValue = 0;
				std::vector<double> posc;
				for(Py_ssize_t c=0; c<numComp; c++)
				{
					PyObject *compObj = PySequence_GetItem(posSrc, c);
					if(compObj == Py_None)
					{	
						noValue = 1;
						posc.push_back(0.);
						continue;
					}
					double comp = PyFloat_AsDouble(compObj);
					posc.push_back(comp);
					if(Py_IS_NAN(comp)) noValue = 1;
					Py_DECREF(compObj);
				}

				if(!noValue)
				{
					//PyObject_Print(posDst, stdout, Py_PRINT_RAW);
					PyObject *destXobj = PySequence_GetItem(posDst, 0);
					PyObject *destYobj = PySequence_GetItem(posDst, 1);
					if(destXobj == NULL || destYobj == NULL)
					{
						PyErr_Format(PyExc_RuntimeError, "Failed to convert position to PyObject");
						//TODO fix possible memory leaks?
				 		return 0;
					}

					long destX = PyLong_AsLong(destXobj);
					long destY = PyLong_AsLong(destYobj);
					class PxInfo pxInfo;
					pxInfo.camId = camId;
					pxInfo.x = posc[0];
					pxInfo.y = posc[1];
					mapping[destX][destY].push_back(pxInfo);

					Py_DECREF(destXobj);
					Py_DECREF(destYobj);
				}

				Py_DECREF(posSrc);
				Py_DECREF(posDst);
			}

			Py_DECREF(pixMapping);
		}
		else
		{
			std::cout << "Warning: PyObject_Call to proj returned null" << std::endl;
		}
		Py_DECREF(projArgs);
		Py_DECREF(camProj);
		Py_DECREF(camData);
	}


	//Clean up	
	if(worldPix != NULL) Py_DECREF(worldPix);
	Py_DECREF(unProjArgs);
	Py_DECREF(outUnProj);

	Py_DECREF(imgPix);

	Py_DECREF(addedPhotos);
	Py_DECREF(addedPhotosItems);

*/
	
	int argc = 1; 
	char *arg1 = new char[9];
	strcpy(arg1, "pano.dll");
	char **argv = &arg1;
	glutInit(&argc, argv);
	glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH);
	glutInitWindowSize(outWidth, outHeight);
	int glut_id = glutCreateWindow("VWGL");
	//glutHideWindow();
	delete [] arg1;

	glutCloseFunc(GlutWindowCloseEvent);

	glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION);

	glClearColor(0,0,0,0);
	glClear(GL_COLOR_BUFFER_BIT);

	glBegin(GL_TRIANGLES);
	{
		glColor3f(1,0,0);
		glVertex2f(0,0);

		glColor3f(0,1,0);
		glVertex2f(.5,0);

		glColor3f(0,0,1);
		glVertex2f(.5,.5);
	}
	glEnd();

	glutSwapBuffers();
	return 0;
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
	
	//char *pxOutRaw = new char[pxOutSize];

	Py_ssize_t numSources = PySequence_Size(images);
	Py_ssize_t numMetas = PySequence_Size(metas);
	if(numSources != numMetas)
	{
		PyErr_Format(PyExc_RuntimeError, "Number of sources and metas must match.");
		Py_DECREF(images);
		Py_DECREF(metas);
 		return NULL;
	}

	//Create output image buffer
	unsigned pxOutSize = 3 * self->outImgH * self->outImgW;
	PyObject *pxOut = PyByteArray_FromStringAndSize("", 0);
	PyByteArray_Resize(pxOut, pxOutSize);
	char *pxOutRaw = PyByteArray_AsString(pxOut);

	//Initialize output image colour
	memset(pxOutRaw, 0x00, pxOutSize);

	//Iterate over cameras in arrangement
	PyObject *addedPhotos = PyObject_GetAttrString(self->cameraArrangement, "addedPhotos");
	if(addedPhotos==NULL) throw std::runtime_error("addedPhotos pointer is null");
	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	if(addedPhotosItems==NULL) throw std::runtime_error("addedPhotosItems pointer is null");
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);
	
	for(Py_ssize_t i=0; i<numCams; i++)
	{
		//Check positions in source image of world positions
		PyObject *camDataTup = PySequence_GetItem(addedPhotosItems, i);
		PyObject *camIdObj = PyTuple_GetItem(camDataTup, 0);
		long camId = PyLong_AsLong(camIdObj);
		PyObject *camData = PyTuple_GetItem(camDataTup, 1);

		//PyObject_Print(camData, stdout, Py_PRINT_RAW); std::cout << std::endl;

		//Get meta data from python objects
		PyObject *pyImage = PySequence_GetItem(images, i);
		if(pyImage==NULL) throw std::runtime_error("pyImage pointer is null");
		PyObject *metaObj = PySequence_GetItem(metas, i);
		if(metaObj==NULL) throw std::runtime_error("metaObj pointer is null");

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

		//Get texture handle
		GLuint texture;
		glGenTextures(1, &texture);
		glBindTexture(GL_TEXTURE_2D, texture);

		//Convert to powers of two shape
		unsigned char *openglTex = NULL;
		unsigned openglTexLen = 0, openglTxWidth = 0, openglTxHeight = 0;

		int texOk = ResizeToPowersOfTwo((unsigned char *)imgRaw, 
			sourceWidth, sourceHeight, 
			sourceFmt.c_str(), &openglTex, &openglTexLen,
			&openglTxWidth, &openglTxHeight);

		if(openglTex!=NULL)
		{

			if(texOk)
			{
				//Load texture into opengl
				glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, openglTxWidth, 
					openglTxHeight, 0, GL_RGB, GL_UNSIGNED_BYTE, openglTex);

				glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
				glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);

			}
			delete [] openglTex;
			openglTex = NULL;
		}

		glClear(GL_COLOR_BUFFER_BIT);
		glColor3d(1.,1.,1.);
		glBindTexture(GL_TEXTURE_2D, texture);
		glBegin(GL_QUADS);
		glTexCoord2d(0.0,0.0);
		glVertex2f(-1,-1);
		glTexCoord2d(1.0,0.0);
		glVertex2f(1,-1);
		glTexCoord2d(1.0,1.0);
		glVertex2f(1,1);
		glTexCoord2d(0.0,1.0);
		glVertex2f(-1,1);
		glEnd();

		//Generate python list of source image positions
		PyObject *imgPix = PyList_New(0);
		for(int xstep = 0; xstep < 10; xstep ++)
		{
			for(int ystep = 0; ystep < 10; ystep ++)
			{
				double x = sourceWidth * double(xstep) / 9.;
				double y = sourceHeight * double(ystep) / 9.;

				PyObject *tupleTemp = PyTuple_New(2);
				PyTuple_SetItem(tupleTemp, 0, PyInt_FromLong(x));
				PyTuple_SetItem(tupleTemp, 1, PyInt_FromLong(y));
				PyList_Append(imgPix, tupleTemp);
				Py_DECREF(tupleTemp);		

			}
		}

		//Transfrom image source positions to world coordinates
		PyObject *camUnProj = PyObject_GetAttrString(camData, "UnProj");
		if(camUnProj==NULL)
			throw std::runtime_error("UnProj method not defined");

		PyObject *unprojArgs = PyTuple_New(1);
		PyTuple_SetItem(unprojArgs, 0, imgPix);
		Py_INCREF(imgPix);

		PyObject *worldPos = PyObject_Call(camUnProj, unprojArgs, NULL);

		



		//Delete opengl texture
		GLuint texArr[1];
		texArr[0] = texture;
		glDeleteTextures(1, texArr);

		Py_DECREF(worldPos);
		Py_DECREF(unprojArgs);
		Py_DECREF(imgPix);
		Py_DECREF(pyImage);
		Py_DECREF(metaObj);
		Py_DECREF(camDataTup);
	}


	//double time1 = double(clock()) / CLOCKS_PER_SEC;
	//std::cout << "Time1 " << time1 - startTime << std::endl;
	/*
	//Get source buffers and meta
	std::vector<unsigned char *> srcBuffs;
	std::vector<PyObject *> srcObjs;
	std::vector<long> srcWidth, srcHeight, srcBuffLen;

	for(Py_ssize_t i=0; i<numSources; i++)
	{
		int imageMetaErr = 0;
		PyObject *srcObj = PySequence_GetItem(images, i);
		PyObject *metaObj = PySequence_GetItem(metas, i);

		srcObjs.push_back(srcObj);
		srcBuffs.push_back((unsigned char *)PyByteArray_AsString(srcObj));
		srcBuffLen.push_back(PyByteArray_Size(srcObj));
		//PyObject_Print(metaObj, stdout, Py_PRINT_RAW);
		
		PyObject *widthObj = PyDict_GetItemString(metaObj, "width");
		if(widthObj!=NULL)
		{
			srcWidth.push_back(PyInt_AsLong(widthObj));
		}
		else
			imageMetaErr = 1;

		PyObject *heightObj = PyDict_GetItemString(metaObj, "height");
		if(heightObj != NULL)
		{
			srcHeight.push_back(PyInt_AsLong(heightObj));
		}
		else
			imageMetaErr = 2;

		PyObject *formatObj = PyDict_GetItemString(metaObj, "format");
		if(formatObj != NULL)
		{
			if(strcmp(PyString_AsString(formatObj), "RGB24")!=0)
				imageMetaErr = 4;
		}
		else
			imageMetaErr = 3;

		Py_DECREF(metaObj);
	

		if(imageMetaErr>0)
		{
			PyErr_Format(PyExc_RuntimeError, "Image source error.");
 			Py_RETURN_NONE;
		}
	}
*/

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

	//Free source objects
	/*for(unsigned i=0; i<srcObjs.size(); i++)
	{
		Py_DECREF(srcObjs[i]);
	}
	srcObjs.clear();*/

	Py_DECREF(images);
	Py_DECREF(metas);

	//double endTime = double(clock()) / CLOCKS_PER_SEC;
	//std::cout << "PanoView_Vis " << endTime - startTime << std::endl;

	Py_DECREF(addedPhotos);
	Py_DECREF(addedPhotosItems);

	glutSwapBuffers();
	PrintGlErrors();

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
