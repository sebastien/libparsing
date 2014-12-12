#include "parsing.h"
#include "oo.h"

// SEE: http://stackoverflow.com/questions/18329532/pcre-is-not-matching-utf8-characters
// HASH: search.h, hcreate, hsearch, etc

Match Word_match(ParsingElement* this, Context* context) {
	return FAILURE;
}

Match Token_match(ParsingElement* this, Context* context) {
	// NOTE: We'll use POSIX's regexp for now
	return FAILURE;
}

Match Procedure_match(ParsingElement* this, Context* context) {
	return FAILURE;
}

/**
 * Returns the next step for this parsing element, based on the given step.
 * The returned step could be the same, updated step, or a new step.
*/
ParsingStep* ParsingElement_next(ParsingElement* this, ParsingStep* step) {

}

// Match* ParsingElement_match(ParsingElement* this, Context* step) {
// }
// Match* ParsingElement_process(ParsingElement* this, Context* step) {
// }

void Parser_parse(Parser* this, Iterator* iterator) {
}

// ----------------------------------------------------------------------------
//
// FILE INPUT
//
// ----------------------------------------------------------------------------

FileInput* FileInput_new(const char* path, unsigned int bufferSize ) {
	__ALLOC(FileInput, this);
	assert(this != NULL);
	// We open the file
	this->file = fopen(path, "r");
	if (this->file==NULL) {
		ERROR("Cannot open file: %s", path);
		__DEALLOC(this);
		return NULL;
	} else {
		// And allocate the buffer
		this->bufferSize = bufferSize;
		this->buffer     = malloc(sizeof(char) * bufferSize);
		return this;
	}
}

void FileInput_destroy(FileInput* this) {
	if (this->file != NULL) { fclose(this->file);   }
	__DEALLOC(this->buffer);
}

// ----------------------------------------------------------------------------
//
// ITERATOR
//
// ----------------------------------------------------------------------------

Iterator* Iterator_new( void ) {
	__ALLOC(Iterator, this);
	return this;
}

bool Iterator_open( Iterator* this, const char *path ) {
	NEW(FileInput,input, path,65000);
	if (input!=NULL) {
		this->input          = (void*)input;
		this->context.status = STATUS_PROCESSING;
		this->context.offset = 0;
		ENSURE(input->file) {};
		return TRUE;
	} else {
		return FALSE;
	}
}

Context* Iterator_next( Iterator* this ) {
	size_t read = fread(
		&(this->context.current),
		sizeof(iterated_t),
		1,
		((FileInput*)this->input)->file
	);
	this->context.offset += read;
	if (read == 0) {
		this->context.status = STATUS_ENDED;
		printf("End reached\n", read);
	} else {
		printf("Read %d bytes\n", read);
	}
	return &(this->context);
}

void Iterator_destroy( Iterator* this ) {
	__DEALLOC(this);
}

int main (int argc, char* argv[]) {
	NEW(Iterator, i);
	Iterator_open(i, "expression.txt");
	Context* context = NULL;
	while (context == NULL || context->status != STATUS_ENDED) {
		context = Iterator_next(i);
		printf("Read: %c at %d\n", context->current, context->offset);
	}
}

// EOF
