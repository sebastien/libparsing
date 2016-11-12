
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


Notes
=====



# Lazy: we need to call process recursively, or make process async and 
# use await.
def on_Computation( match ):
	left = match[0]

# Non-lazy: stuff is pre-calculated
def on_Computation( match ):
	left = match[0]
	righ = match[1]

# And in this case, we would do something like

Match->result;

	void Match__createResult( Match*, ProcessCallback callback )

where 

	void* callback(Match*)

if we do this, then we can move the processor to C code, and simply give
a mapping [symbol id]->callback. The implementation would be like

	Match* child = match->children;
	while (child !=NULL ) {
		Match__createResult(child, callback);
		child = child->next;
	}
	// Now the match children all have results
	match->result = callback(match);
	
and the dispatching callback

	void Processor_dispatch( Match* match, ProcessCallback[] callbacks, ProcessCallback default ) {
		ProcessCallback callback = callbacks[match->element->id];
		if (callback == NULL) {
			default(match);
		} else {
			callback(match);
		}
	}

also

	Processor_register(Processor*,   ParsingElement*,  ParsingCallback)
	Processor_unregister(Processor*, ParsingElement*, ParsingCallback)
	Processor_default(Processor*,  ParsingCallback)
	Processor_process(Processor* this, Match* match)

and in Python. This would very probably make it faster, but only if the processor
is a full Python extension, as otherwise we'll pay for callback cost.


