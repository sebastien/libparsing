#ifdef WITH_PYTHON
#ifndef __PARSING_PYTHON_H__
#define __PARSING_PYTHON_H__

#include <Python.h>

int Parsing_getPythonVersion();
PyObject* Match_processPython( Match* match, PyObject* callback );

#endif
#endif
