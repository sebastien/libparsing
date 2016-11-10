#ifdef WITH_PYTHON
#include <Python.h>
#include "parsing"

void Processor_dispatchPython( Match* match, PyObject* callbacks ) {
	int i  = PyList_Size(callbacks);
	int id = match->element->id;
	assert(id < i)
		sdadsas
}

#endif
