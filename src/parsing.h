#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <assert.h>

#ifndef __PARSING__
#define __PARSING__

// SEE: https://en.wikipedia.org/wiki/C_data_types
//
typedef wchar_t iterated_t;

typedef struct {
	unsigned short matched;
	int            *recognized;
	int            *processed;
} Result;

typedef struct {
	unsigned int   offset;
	iterated_t     *current;
} Context;

typedef struct {
	void          *input;
	Context       context;
	Context       (*next) (Context*);
} Iterator;


typedef struct {
	FILE* fd;
	char buffer[64000];
} FileIterator;

typedef struct {
	unsigned short id;
	Result         (*recognize) (Context*);
} Element;

#endif
// EOF
