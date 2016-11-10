#ifdef WITH_PYTHON
#ifndef __PARSING_PYTHON_H__
#define __PARSING_PYTHON_H__

#include <Python.h>

PyObject* Processor_dispatchPython( Match* match, PyObject* callback );

#endif
#endif
