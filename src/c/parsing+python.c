#ifdef WITH_PYTHON
#include <Python.h>
#include "parsing.h"

// SEE: http://stackoverflow.com/questions/10247779/python-c-api-functions-that-borrow-and-steal-references#10250720
PyObject* Processor_dispatchPython( Match* match, PyObject* callbacks ) {
	if (match == NULL) {return NULL;}

	int i                   = PyList_Size(callbacks);
	ParsingElement* element = (ParsingElement*)match->element;
	PyObject* callback      = PyList_GET_ITEM(callbacks, element->id);
	PyObject* value         = NULL;

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
				break;
			default:
				break;
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

	PyObject* range  = Py_BuildValue("(i,i)", match->offset, match->offset + match->length);
	PyObject* args   = PyTuple_Pack(2, value ,range);
	PyObject* result = PyObject_CallObject(callback, args);

	Py_DECREF(value);
	Py_DECREF(range);
	Py_DECREF(args);
	return result;

}

#endif
