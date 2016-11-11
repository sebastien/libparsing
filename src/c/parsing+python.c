#ifdef WITH_PYTHON
#include <Python.h>
#include "parsing.h"

// SEE: http://stackoverflow.com/questions/10247779/python-c-api-functions-that-borrow-and-steal-references#10250720
PyObject* Processor_dispatchPython( Match* match, PyObject* callbacks ) {

	if (match == NULL) {return NULL;}

	if(!Py_IsInitialized())
	{
		Py_Initialize();
		PyEval_InitThreads(); //Initialize Python thread ability
		PyEval_ReleaseLock(); //Release the implicit lock on the Python GIL
	}

	Py_XINCREF(callbacks);
	ParsingElement* element = (ParsingElement*)match->element;
	PyObject* callback      = PyList_Check(callbacks) && PyList_GET_SIZE(callbacks) > element->id ? PyList_GetItem(callbacks, element->id) : NULL;
	PyObject* value         = NULL;
	Py_XINCREF(callback);

	int count               = Match_countChildren(match);

	if (count==0) {
		switch (element->type) {
			case TYPE_WORD:
				value = Py_BuildValue("(i,i,s)", match->offset, match->offset + match->length, Word_word(element));
				break;
			case TYPE_TOKEN:
				value = Py_BuildValue("(i,i,s)", match->offset, match->offset + match->length, "token");
				break;
			case TYPE_CONDITION:
			case TYPE_PROCEDURE:
			default:
				value = Py_None;
				Py_INCREF(value);
		}
	}
	else {
		value = PyTuple_New(count);
		Match* child    = match->children;
		for( int i=0 ; i<count ; i++) {
			if (child != NULL) {
				PyObject* item = Processor_dispatchPython(child, callbacks);
				// We don't need to increase the reference as the result is
				// expected to be referenced
				PyTuple_SET_ITEM(value, i, item);
			}
			child = child->next;
		}
		// SEE: http://stackoverflow.com/questions/3286448/calling-a-python-method-from-c-c-and-extracting-its-return-value

	}

	// NOTE: New versions of Python have PyCallable_Check
	// SEE:  http://svn.python.org/projects/python/trunk/Objects/object.c
	if (callback!=NULL && PyFunction_Check(callback) ) {
		assert(value != NULL);
		printf("Is callable!\n");
		PyObject* range  = Py_BuildValue("(i,i)", match->offset, match->offset + match->length);
		PyObject* args   = Py_BuildValue("(i)",1);
		// NOTE: This is super important, as otherwise it segfaults
		PyGILState_STATE gstate; gstate = PyGILState_Ensure();
		PyObject* result = PyObject_CallObject(callback, args);
		PyGILState_Release(gstate);
		Py_DECREF(value);
		Py_DECREF(range);
		Py_DECREF(args);
		Py_XDECREF(callback);
		Py_XDECREF(callbacks);
		return result;
	} else {
		Py_XDECREF(callback);
		Py_XDECREF(callbacks);
		return value;
	}

}

#endif
