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
#include <map>
#include <vector>
#include <stdexcept>
#include <pthread.h>

class PanoView_cl{
public:
	PyObject_HEAD

	std::vector<std::vector<std::vector<class PxInfo> > > *mapping;
	long outImgW, outImgH;
};
typedef PanoView_cl PanoView;

static PyObject *TestFunc(PyObject *self, PyObject *args)
{
	Py_RETURN_NONE;
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

	if(self->mapping) delete self->mapping;
	self->mapping = NULL;

	self->ob_type->tp_free((PyObject *)self);
}

static int PanoView_init(PanoView *self, PyObject *args,
		PyObject *kwargs)
{
	self->mapping = new std::vector<std::vector<std::vector<class PxInfo> > >;

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

	PyObject *outWidthObj = PyObject_GetAttrString(outProj, "imgW");
	PyObject *outHeightObj = PyObject_GetAttrString(outProj, "imgH");
	long outWidth = PyInt_AsLong(outWidthObj);
	long outHeight = PyInt_AsLong(outHeightObj);
	self->outImgW = outWidth;
	self->outImgH = outHeight;
	
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

		//PyObject_Print(test, stdout, Py_PRINT_RAW); std::cout << std::endl;

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
				int nan = 0;
				std::vector<double> posc;
				for(Py_ssize_t c=0; c<numComp; c++)
				{
					PyObject *compObj = PySequence_GetItem(posSrc, c);
					double comp = PyFloat_AsDouble(compObj);
					posc.push_back(comp);
					if(Py_IS_NAN(comp)) nan = 1;
					Py_DECREF(compObj);
				}

				if(!nan)
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

	Py_DECREF(outWidthObj);
	Py_DECREF(outHeightObj);

	return 0;
}

static PyObject *PanoView_Vis(PanoView *self, PyObject *args)
{

	if(PyTuple_Size(args) < 2)
	{
		PyErr_Format(PyExc_RuntimeError, "Two arguments required.");
 		Py_RETURN_NONE;
	}

	PyObject *images = PyTuple_GetItem(args, 0);
	PyObject *metas = PyTuple_GetItem(args, 1);
	std::vector<std::vector<std::vector<class PxInfo> > > &mapping = *self->mapping;

	//Create output image buffer
	

	//PyObject *pxOut = PyByteArray_FromStringAndSize("", 0);
	//PyByteArray_Resize(pxOut, 3 * self->outImgH * self->outImgW);
	//PyByteArray_AsString(pxOut);
	unsigned pxOutSize = 3 * self->outImgH * self->outImgW;
	char *pxOutRaw = new char[pxOutSize];

	Py_ssize_t numSources = PySequence_Size(images);
	Py_ssize_t numMetas = PySequence_Size(metas);
	if(numSources != numMetas)
	{
		PyErr_Format(PyExc_RuntimeError, "Number of sources and metas must match.");
 		Py_RETURN_NONE;
	}

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
			Py_DECREF(widthObj);
		}
		else
			imageMetaErr = 1;

		PyObject *heightObj = PyDict_GetItemString(metaObj, "height");
		if(heightObj != NULL)
		{
			srcHeight.push_back(PyInt_AsLong(heightObj));
			Py_DECREF(heightObj);
		}
		else
			imageMetaErr = 2;

		PyObject *formatObj = PyDict_GetItemString(metaObj, "format");
		if(formatObj != NULL)
		{
			if(strcmp(PyString_AsString(formatObj), "RGB24")!=0)
				imageMetaErr = 4;
			Py_DECREF(formatObj);
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

	//Initialize output image colour
	for(long y=0; y < self->outImgH; y++)
	for(long x=0; x < self->outImgW; x++)
	{
		unsigned char *dstRgbTuple = (unsigned char *)&pxOutRaw[x*3 + y*3*self->outImgW];
		dstRgbTuple[0] = 0;
		dstRgbTuple[1] = 0;
		dstRgbTuple[2] = 0;
	}

	//Transfer source images to output buffer
	for(long y=0; y < self->outImgH; y++)
	for(long x=0; x < self->outImgW; x++)
	{
		unsigned char *dstRgbTuple = (unsigned char *)&pxOutRaw[x*3 + y*3*self->outImgW];

		std::vector<class PxInfo> &sources = mapping[x][y];
		for(unsigned srcNum = 0; srcNum <sources.size(); srcNum++)
		{ 
			class PxInfo &pxInfo = sources[srcNum];
			unsigned char *srcBuff = srcBuffs[pxInfo.camId];
			long sw = srcWidth[pxInfo.camId];
			long sh = srcHeight[pxInfo.camId];

			//Nearest neighbour pixel
			long srx = (int)(pxInfo.x+0.5);
			long sry = (int)(pxInfo.y+0.5);

			if(srx<0 || srx >= sw) continue;
			if(sry<0 || sry >= sh) continue;

			unsigned tupleOffset = srx*3 + sry*3*sw;
			if(tupleOffset < 0 || tupleOffset+3 >= srcBuffLen[pxInfo.camId])
				continue; //Protect against buffer overrun
			unsigned char *srcRgbTuple = (unsigned char *)&srcBuff[tupleOffset];

			//Copy pixel
			dstRgbTuple[0] = srcRgbTuple[0];
			dstRgbTuple[1] = srcRgbTuple[1];
			dstRgbTuple[2] = srcRgbTuple[2];

		}
	}

	PyObject *pxOut = PyByteArray_FromStringAndSize(pxOutRaw, pxOutSize);
	delete [] pxOutRaw;
	pxOutRaw = NULL;

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
	for(unsigned i=0; i<srcObjs.size(); i++)
	{
		Py_DECREF(srcObjs[i]);
	}
	srcObjs.clear();

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
			0, Py_TPFLAGS_DEFAULT, "PanoView()\n\n", 0, 0, 0,
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
