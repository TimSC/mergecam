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

	

};
typedef PanoView_cl PanoView;

static PyObject *TestFunc(PyObject *self, PyObject *args)
{
	Py_RETURN_NONE;
}

// **********************************************************************

static void PanoView_dealloc(PanoView *self)
{

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

	PyObject *outWidthObj = PyObject_GetAttrString(outProj, "imgW");
	PyObject *outHeightObj = PyObject_GetAttrString(outProj, "imgH");
	long outWidth = PyInt_AsLong(outWidthObj);
	long outHeight = PyInt_AsLong(outHeightObj);
	
	//Create list of screen coordinates
	std::cout << outWidth << "," << outHeight << std::endl;
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
 		return 0;
	}


	PyObject *unProjArgs = PyTuple_New(1);
	PyTuple_SetItem(unProjArgs, 0, imgPix);
	Py_INCREF(imgPix);
	PyObject *worldPix = PyObject_Call(outUnProj, unProjArgs, NULL);

	//Iterate over cameras in arrangement
	PyObject *cameraArragement = PyTuple_GetItem(args, 0);
	PyObject *addedPhotos = PyObject_GetAttrString(cameraArragement, "addedPhotos");
	if(addedPhotos==NULL)
	{
		PyErr_Format(PyExc_RuntimeError, "addedPhotos dict not defined");
 		return 0;
	}

	PyObject *addedPhotosItems = PyDict_Items(addedPhotos);
	Py_ssize_t numCams = PySequence_Size(addedPhotosItems);

	for(Py_ssize_t i=0; i<numCams; i++)
	{
		//Check positions in source image of world positions
		PyObject *camDataTup = PySequence_GetItem(addedPhotosItems, i);
		PyObject *camData = PyTuple_GetItem(camDataTup, 1);

		//PyObject_Print(camData, stdout, Py_PRINT_RAW);
		PyObject *camProj = PyObject_GetAttrString(camData, "Proj");
		if(camProj==NULL)
		{
			PyErr_Format(PyExc_RuntimeError, "Proj method not defined");
	 		return 0;
		}

		PyObject *projArgs = PyTuple_New(1);
		PyTuple_SetItem(projArgs, 0, worldPix);
		Py_INCREF(projArgs);

		PyObject *pixMapping = PyObject_Call(camProj, projArgs, NULL);

		if(pixMapping != NULL)
		{
			Py_ssize_t numPix = PySequence_Size(pixMapping);

			for(Py_ssize_t j=0; j<numPix; j++)
			{
				PyObject *pos = PySequence_GetItem(pixMapping, j);
				//PyObject_Print(pos, stdout, Py_PRINT_RAW);
				
				Py_ssize_t numComp = PySequence_Size(pos);
				int nan = 0;
				for(Py_ssize_t c=0; c<numComp; c++)
				{
					PyObject *compObj = PySequence_GetItem(pos, c);
					double comp = PyFloat_AsDouble(compObj);
					std::cout << comp << ",";
					if(Py_IS_NAN(comp)) nan = 1;
					Py_DECREF(compObj);
				}
				std::cout << nan << std::endl;

				Py_DECREF(pos);
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

	Py_RETURN_NONE;
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
