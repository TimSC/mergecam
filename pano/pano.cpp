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

class Test_cl{
public:
	PyObject_HEAD
	int val;
};
typedef Test_cl Test;

static PyObject *TestFunc(PyObject *self, PyObject *args)
{
	Py_RETURN_NONE;
}

// **********************************************************************

static void Test_dealloc(Test *self)
{

	self->ob_type->tp_free((PyObject *)self);
}

static int Test_init(Test *self, PyObject *args,
		PyObject *kwargs)
{
	return 0;
}

static PyObject *Test_Test(Test *self, PyObject *args)
{
	Py_RETURN_NONE;
}

// *********************************************************************

static PyMethodDef Test_methods[] = {
	{"test", (PyCFunction)Test_Test, METH_VARARGS,
			 "test()\n\n"
			 "Test func"},
	{NULL}
};

static PyTypeObject Test_type = {
	PyObject_HEAD_INIT(NULL)
			0, "v4l2capture.Test", sizeof(Test), 0,
			(destructor)Test_dealloc, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
			0, Py_TPFLAGS_DEFAULT, "Test()\n\n", 0, 0, 0,
			0, 0, 0, Test_methods, 0, 0, 0, 0, 0, 0, 0,
			(initproc)Test_init
};

// *********************************************************************

static PyMethodDef module_methods[] = {
	{ "testfunc", (PyCFunction)TestFunc, METH_VARARGS, NULL },
	{ NULL, NULL, 0, NULL }
};

PyMODINIT_FUNC initpano(void)
{
	Test_type.tp_new = PyType_GenericNew;

	if(PyType_Ready(&Test_type) < 0)
		{
			return;
		}

	PyObject *module = Py_InitModule3("pano", module_methods,
			"pano tools.");

	if(!module)
		{
			return;
		}

	Py_INCREF(&Test_type);
	PyModule_AddObject(module, "Test", (PyObject *)&Test_type);

}
