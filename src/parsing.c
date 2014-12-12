#include "parsing.h"
#include "oo.h"

Iterator* Iterator_new( void ) {
	__ALLOC(Iterator, this);
	return this;
}

void Iterator_open( Iterator* this, const char *path ) {
	__ALLOC(FileIterator, input);
	this->input = (void*)input;
	input->fd = fopen(path, "r");
	ENSURE(input->fd) {};
}

void Iterator_destroy( Iterator* this ) {
	__DEALLOC(this);
}

int main (int argc, char* argv[]) {
	NEW(Iterator, i);
	Iterator_open(i, "expression.txt");
}

// EOF
