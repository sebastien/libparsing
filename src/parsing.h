#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <assert.h>

#ifndef __PARSING__
#define __PARSING__

#define STATUS_INIT       '-'
#define STATUS_PROCESSING '~'
#define STATUS_MATCHED    'Y'
#define STATUS_FAILED     'X'
#define STATUS_ENDED      'E'

#define TYPE_SINGLE       '1'
#define TYPE_OPTIONAL     '?'
#define TYPE_ZERO_OR_MORE '*'
#define TYPE_ONE_OR_MORE  '+'

// SEE: https://en.wikipedia.org/wiki/C_data_types


/**
 * The parser is configured to iterate on specific elements of input.
 * In that case, we'll iterate over chars.
*/
typedef char iterated_t;

/**
 * A parsing result defines the number of matched `iterated_t`
 * and holds a `recognized` result and a `processed` result.
*/
typedef struct {
	unsigned short matched;
	int            *recognized;
	int            *processed;
} Match;
typedef Match Result;

/**
 * The context holds an offset within the iterated input, the current
 * `iterated_t` value (as well as what has already been parsed), as well the
 * status of the parsing.
*/
typedef struct {
	char           status;
	unsigned int   offset;
	unsigned int   lines;    // Counter for lines that have been encountered
	// FIXME: Current should a pointer within the head
	iterated_t     current;
	// FIXME: The head should be freed when the offsets have been parsed,
	// no need to keep in memory stuff we won't need.
	iterated_t*    head;
} Context;

/*
 * An iterator wraps a context in an input and a next function that
 * allow to update the iterated_t
*/
typedef struct {
	void          *input;
	Context       context;
	Context*      (*next) (Context*);
} Iterator;

/**
 * Using a file as an input
*/
typedef struct {
	FILE* file;
} FileInput;

typedef struct Reference Reference;

/***
 * A parsing element has an `id` that corresponds to its bread-first distance
 * to the axiom. It can try to `match` an input and then `process` the resulting
*/
typedef struct ParsingElement {
	unsigned short id;         // The ID, assigned by the grammar, as the relative distance to the axiom
	const char    *name;       // The parsing element's name, for debugging
	void          *args;       // The configuration of the parsing element
	// FIXME: These should be references
	Reference* children;
	Match            (*match)     (struct ParsingElement*, Context*);
	Result           (*process)   (struct ParsingElement*, Context*, Match*);
} ParsingElement;

/**
 * A reference references a parsing element, allowing to name it, give
 * it a cardinality and create a chain.
*/
typedef struct Reference {
	char            cardinality;
	const char*     name;
	ParsingElement* element;
	Reference*      next;
} Reference;

/**
 * The parsing step allows to memoize the state of a parsing element at a given
 * offset. This is the data structure that will be manipulated and created/destroyed
 * the most during the parsing process.
*/
typedef struct ParsingStep {
	// FIXME: Might just refernce the ParsingElement instead, this would save
	// querying the grammar
	unsigned short pid;           // ParsingElement.id, which represents the distance to the axio
	char           step;          // We don't expect more than 256 step / parsing element
	unsigned int   iteration;     // The current iteration (on the step)
	char           status;        // PARSING_STATUS
	Result*        result;        // The current result, if any
	struct ParsingStep* previous; // The previous parsing step
} ParsingStep;

/**
 * The parsing offset is a stack of parsing steps, where the tail is the most
 * specific parsing step. By following the tail's previous parsing step,
 * you can unwind the stack.
 *
 * The parsing steps each have an offset within the iterated stream. Offsets
 * where data has been fully extracted (ie, a leaf parsing element has matched
 * and processing returned a NOTHING) can be freed as they are not necessary
 * any more.
*/
typedef struct ParsingOffset {
	unsigned long         offset;
	ParsingStep*          tail;
	struct ParsingOffset* next;
} ParsingOffset;

/*
 * The grammar has one parsing element as the axiom.
*/
typedef struct {
	ParsingElement* axiom;       // The axiom
	ParsingElement* skip;        // The skipped element
	ParsingElement* elements[];  // The elements, accessible by ID
} Grammar;

typedef struct {
	Grammar       *grammar;      // The grammar
	ParsingOffset *head;         // The smallest offset that has yet to be processed
	ParsingOffset *current;      // The current offset to be processed
} Parser;

Match  FAILURE;
Result NOTHING;

#endif
// EOF
