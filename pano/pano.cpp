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

	PyObject *cameraArragement = PyTuple_GetItem(args, 0);

	PyObject *addedPhotos = PyObject_GetAttrString(cameraArragement, "addedPhotos");
	std::cout << "PyDict_Check " << PyDict_Check(addedPhotos) << std::endl;

	Py_DECREF(addedPhotos);

	PyObject *outProj = PyTuple_GetItem(args, 1);
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
	
	PyObject *unProjArgs = PyTuple_New(1);
	PyTuple_SetItem(unProjArgs, 0, imgPix);
	PyObject *out = PyObject_Call(outUnProj, unProjArgs, NULL);


	




	//Clean up	

	if(out != Py_None) Py_DECREF(out);
	Py_DECREF(unProjArgs);
	Py_DECREF(outUnProj);

	Py_DECREF(imgPix);

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
