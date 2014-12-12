#include "parsing.h"
#include "oo.h"

Iterator* Iterator_new( void ) {
	__ALLOC(Iterator, this);
	return this;
}

void Iterator_open( Iterator* this, const char *path ) {
	__ALLOC(FileInput, input);
	this->input = (void*)input;
	input->file = fopen(path, "r");
	this->context.status=STATUS_PROCESSING;
	this->context.offset=0;
	ENSURE(input->file) {};
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
