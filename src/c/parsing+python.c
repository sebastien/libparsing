#ifdef WITH_PYTHON
#include <Python.h>
#include <frameobject.h>
#include "parsing.h"

// SEE: http://dan.iel.fm/posts/python-c-extensions/
// TOOD: This needs to be a separate Python module named "_libparsing_helpers",
// defining "ParsingException" and
//
int Parsing_getPythonVersion() {
#ifdef WITH_PYTHON3
	return 3;
#else
	return 2;
#endif
}

inline void Match_onPythonError(Match* match) {
	PyGILState_STATE gil = PyGILState_Ensure ();
	PyObject *type, *value, *traceback;
	PyErr_Fetch(&type, &value, &traceback);
	PyTracebackObject* tb = traceback;
	char *error           = PyString_AsString(value);
	PyFrameObject* frame  = tb->tb_frame;
	printf("libparsing error:" BOLDRED "%s" RESET "\n", error);
	while (frame != NULL)
	{
		char const* filename = PyString_AsString(frame->f_code->co_filename);
		char const* name     = PyString_AsString(frame->f_code->co_name);
		printf(" at " YELLOW "%s" RESET ":" BOLDWHITE "%d " RESET RED "%s " RESET "\n", filename, PyFrame_GetLineNumber(frame), name);
		frame = frame->f_back;
	}
	PyGILState_Release(gil);
}


// SEE: http://stackoverflow.com/questions/10247779/python-c-api-functions-that-borrow-and-steal-references#10250720
PyObject* Match_processPython( Match* match, PyObject* callbacks ) {

	if (match == NULL) {return NULL;}

	if(!Py_IsInitialized())
	{
		Py_Initialize();
		PyEval_InitThreads(); //Initialize Python thread ability
		PyEval_ReleaseLock(); //Release the implicit lock on the Python GIL
	}

	Py_XINCREF(callbacks);
	ParsingElement* element = (ParsingElement*)match->element;
	PyObject* callback      = PyList_Check(callbacks) && PyList_GET_SIZE(callbacks) > element->id && element->id >= 0 ? PyList_GetItem(callbacks, element->id) : NULL;
	PyObject* value         = NULL;
	Py_XINCREF(callback);

	int count               = Match_countChildren(match);

	if (count==0) {
		int n = 0;
		switch (element->type) {
			case TYPE_WORD:
				// A word → string
				value = PyString_FromString(WordMatch_group(match));
				break;
			case TYPE_TOKEN:
				// A token → (string,‥)
				n = TokenMatch_count(match);
				value = PyTuple_New(n);
				for (int i=0 ; i<n ; i++) {
					PyObject* t = PyString_FromString(TokenMatch_group(match, i));
					PyTuple_SET_ITEM(value, i, t);
				}
				break;
			case TYPE_CONDITION:
			case TYPE_PROCEDURE:
			default:
				// Otherwise it's a None
				value = Py_None;
				Py_INCREF(value);
		}
	}
	else if (count == 1 && !Reference_IsMany(match->element)) {
		// If it's not a many reference, we return the result as-is.
		value = Match_processPython(match->children, callbacks);
	} else {
		value = PyTuple_New(count);
		Match* child    = match->children;
		for( int i=0 ; i<count ; i++) {
			if (child != NULL) {
				PyObject* item = Match_processPython(child, callbacks);
				// We don't need to increase the reference as the result is
				// expected to be referenced
				if (item == NULL) {
					Py_DECREF(value);
					value = NULL;
					break;
				} else {
					PyTuple_SET_ITEM(value, i, item);
				}
			} else {
				// However, here we need to increase the refount
				Py_INCREF(Py_None);
				PyTuple_SET_ITEM(value, i, Py_None);
			}
			child = child->next;
		}
		// SEE: http://stackoverflow.com/questions/3286448/calling-a-python-method-from-c-c-and-extracting-its-return-value
	}

	// NOTE: New versions of Python have PyCallable_Check
	// SEE:  http://svn.python.org/projects/python/trunk/Objects/object.c
	PyGILState_STATE gstate;
	if (value == NULL) {
		Match_onPythonError(match);
		return Py_None;
	} else if (callback!=NULL && PyCallable_Check(callback)) {
		PyObject* range  = Py_BuildValue("(i,i)", match->offset, match->offset + match->length);
		PyObject* args   = Py_BuildValue("(O,O,i)", value, range, element->id);
		// NOTE: This is super important, as otherwise it segfaults
		gstate = PyGILState_Ensure();
		PyObject* result = PyObject_CallObject(callback, args);
		PyGILState_Release(gstate);
		Py_DECREF(value);
		Py_DECREF(range);
		Py_DECREF(args);
		Py_XDECREF(callback);
		Py_XDECREF(callbacks);
		if (result == NULL) {
			Match_onPythonError(match);
			// NOTE: We should return NULL, but it segfaults
			// http://stackoverflow.com/questions/39911099/segmentation-fault-with-python-ctypes-when-function-returns-a-null-pyobject-po
			return Py_None;
		} else {
			return result;
		}
	} else {
		Py_XDECREF(callback);
		Py_XDECREF(callbacks);
		return value;
	}

}

#endif
