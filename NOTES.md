
C embedding:

1) Come back to a stable version where PCSS does not abort because of memory
   errors.

2) Test various ways to identify the handler that is being executed and the
   call stack. Usually, if an error happens the current frame will be the handler's.

High-priority:

[ ] Line numbers are not accurage because backtracking does not keep track of them

[ ] Remove ParsingStep, ParsingOffset

[ ] Matches should have a temporary match set as parent, so that it's possible to debug
    and get the current potential matching stack. 

[ ] Error reporting: right now, the Python bindings don't report the current
    text around the failure. What it should do is indicate the line, the character,
	the offset, show one or more previous lines, one or more next lines and
	show the error using a `^` character.


	```
	Parsing failed at line 210, character 20 (offset 618):

	>	}
	>	return self
	>	       ^
	>	@end

	```

	There could be a more verbose mode that shows the list of ancestors of
	the deepest match that had an error, showing which rules have succeeded
	and which ones have failed. Only named rules should be visible, and
	skipped rules should not be visible.

	```
	⨯ Module [618-]
		⨯ Class [619-]
			✓ constructor[700-100]
			⨯ statement [900-]
	```

	This would basically be better than the current verbose mode, which
	is more like a trace mode.

Nice:

[ ] ParsingElement should have a recognize callback to allow debugging specific
    elements. The callback should take (element, match).

[ ] Implement a faster walking/processing algorithm that takes a Python
    object with {<symbol id>:(match,walk)→Any} and is driven by the C code
	and where we limit the wrapping of matches as much as possible.
 
[ ] Detect left recursion in the parsing context -- however this would
    only work with some kind of memoization, but would work within a structure
	of N bits (N=number of parsing elements) and where 0=element never run
	at this position and 1=element already run at that position. This would
	mean that each element would have a parsing context.

[ ] Callbacks for parsing elements, so that you can hook up a processor
    for the parsing stage (and trace stuff). It might be good to enable rules
    such as https://github.com/sirthias/parboiled/wiki/Grammar-and-Parser-Debugging


[ ] Memory management: 

    - ParsingElements should be attached to the grammar, make sure the Python
      objects retain it. Only the grammar should free the elements.

    - Matches should be attached to the parsing context, always, the parsing
      context is responsible for freeing them. Ditto for the iterator.

Maybe:

[ ] Implement a DSL to create the grammar, the programmatic version
    does not work very well.

[ ] Make elements support delegates so that we can dynamically override
    the grammar rules (although in that case the symbol ID would change)


C dispatching
=============

The main issues are regarding logging and memory management.

Python C API
============

Some gotchas when using ctypes to call a function that uses the Python C API:

- Calling a C function using PyObject as parameters/return from ctypes has
  some limitations: you can't return NULL, you can't raise exceptions, and 
  logging errors is a bit difficult.

- When calling back Python from C code called via ctypes, it's important
  to acquire and release the GIL.

- It's easy to get a segfault (duh!)





