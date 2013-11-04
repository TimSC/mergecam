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
#include <sstream>
#include <map>
#include <vector>
#include <stdexcept>
#include <pthread.h>

class PanoView_cl{
public:
	PyObject_HEAD
	int val;
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
	return 0;
}

static PyObject *PanoView_Test(PanoView *self, PyObject *args)
{
	Py_RETURN_NONE;
}

// *********************************************************************

static PyMethodDef PanoView_methods[] = {
	{"test", (PyCFunction)PanoView_Test, METH_VARARGS,
			 "test()\n\n"
			 "Test func"},
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
