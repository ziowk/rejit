#include <Python.h>

#ifdef _WIN32
#include "windows_loadcode.h"
#elif __gnu_linux__
#include "gnu_linux_loadcode.h"
#else
#error "OS not supported!"
#endif

/*----- python code -----*/
static void *
PyCode_AsPtr(PyObject *obj) {
    return (void *) PyCapsule_GetPointer(obj, "code");
}

static void 
del_Code(PyObject *obj) {
    freeFunction((FunObj*)PyCode_AsPtr(obj));
    //PySys_WriteStdout("CODE OBJECT DELETED\n");
}

static PyObject *
PyCode_FromPtr(void *p) {
    return PyCapsule_New(p, "code", del_Code );
}

static PyObject *LoadcodeError;

static PyObject *
loadcode_load(PyObject *self, PyObject *args)
{
    Py_buffer bytes;
    PyObject *code;
    FunObj *funobj;

    if (!PyArg_ParseTuple(args, "y*", &bytes)) // PyBuffer_Release --\/
        return NULL;

    //PySys_WriteStdout("bytes length: %d\n", bytes.len);
    if ((funobj = createFunction(bytes.buf, bytes.len)) == NULL) {
        PyErr_SetString(LoadcodeError, "Allocating jitted function failed");
        return NULL;
    }

    code = PyCode_FromPtr(funobj);

    PyBuffer_Release(&bytes); // PyArg_ParseTuple --^ 

    return code;
}

static PyObject *
loadcode_call(PyObject *self, PyObject *args)
{
    PyObject *capsule; 
    const char* str;
    int len;
    FunObj *funobj;
    int result;

    if (!PyArg_ParseTuple(args, "Osi", &capsule, &str, &len))
        return NULL;

    funobj = (FunObj*)PyCode_AsPtr(capsule);
    result = funobj->func(str, len);

    return PyLong_FromLong(result);
}

static PyMethodDef LoadcodeMethods[] = {
    {"load", loadcode_load, METH_VARARGS,
     "Create a jitted function from bytes"},
    {"call", loadcode_call, METH_VARARGS,
     "Call a jitted function"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef loadcodemodule = {
   PyModuleDef_HEAD_INIT,
   "loadcode",      /* name of module */
   NULL,            /* module documentation, may be NULL */
   -1,              /* size of per-interpreter state of the module,
                       or -1 if the module keeps state in global variables. */
   LoadcodeMethods
};

PyMODINIT_FUNC
PyInit_loadcode(void) {
    PyObject *m;
    PyObject *rejitModule;
    PyObject *rejitExceptionBase;
    PyObject *rejitBaseName = PyUnicode_FromString("RejitError");

    // get base class module
    if ((rejitModule = PyImport_ImportModule("rejit.common")) == NULL) {
        return NULL;
    }
    // get exception base
    if ((rejitExceptionBase = PyObject_GetAttr(rejitModule, rejitBaseName)) == NULL) {
        return NULL;
    }
    Py_DECREF(rejitBaseName); // no longer needed
    // create exception class
    LoadcodeError = PyErr_NewException("loadcode.LoadCodeError", rejitExceptionBase, NULL);
    Py_INCREF(LoadcodeError); /* need to keep a reference because AddObject steals one
                                 but the module keeps a reference anyway so... */
    Py_DECREF(rejitModule); // no longer needed
    Py_DECREF(rejitExceptionBase); // no longer needed

    // create `loadcode` module
    if ((m = PyModule_Create(&loadcodemodule)) == NULL) {
        return NULL;
    }
    // add exception class to the module
    if(PyModule_AddObject(m, "LoadCodeError", LoadcodeError) == -1) {
        return NULL;
    }
    //PySys_WriteStdout("Module loadcode created\n");
    return m;
}

