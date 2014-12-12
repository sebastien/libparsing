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
// REFERENCE
//
// ----------------------------------------------------------------------------

Reference* Reference_new() {
	__ALLOC(Reference, this);
	this->type        = Reference_T;
	this->cardinality = ZERO_OR_MORE;
	this->name        = ANONYMOUS;
	this->element     = NULL;
	this->next        = NULL;
	return this;
}

// ----------------------------------------------------------------------------
//
// PARSING ELEMENT
//
// ----------------------------------------------------------------------------

ParsingElement* ParsingElement_new() {
	__ALLOC(ParsingElement, this);
	this->id       = 0;
	this->name     = ANONYMOUS;
	this->config   = NULL;
	this->children = NULL;
	this->match    = NULL;
	this->process  = NULL;
}

Reference* ParsingElement_asReference(ParsingElement *this) {
	NEW(Reference, ref);
	ref->element = this;
	return ref;
}

ParsingElement* ParsingElement_add(ParsingElement *this, Reference *child) {
	if (ParsingElement_is(child)) {child = ParsingElement_asReference((ParsingElement*)child);}
	assert(child->next == NULL);
	if (this->children) {
		// If there are children, we skip until the end and add it
		Reference* ref = this->children;
		while (ref->next != NULL) {ref = ref->next;}
		ref->next = child;
	} else {
		// If there are no children, we set it as the first
		this->children = child;
	}
	return this;
}

void ParsingElement_destroy(ParsingElement* this) {
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// TOKEN
//
// ----------------------------------------------------------------------------

ParsingElement* Token_new(const char* expr) {
	__ALLOC(TokenConfig, config);
	ParsingElement* this = ParsingElement_new();
	if ( regcomp( &(config->regex), expr, REG_EXTENDED) == 0) {
		this->config = config;
		return this;
	} else {
		ERROR("Cannot compile POSIX regex: %s", expr);
		__DEALLOC(config);
		ParsingElement_destroy(this);
		return NULL;
	}
}

// ----------------------------------------------------------------------------
//
// GROUP
//
// ----------------------------------------------------------------------------

ParsingElement* Group_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new();
	// FIXME: Make sure how memory is managed here
	Reference* r = *children;
	while ( r != NULL ) {
		if (ParsingElement_is(r)) {r = ParsingElement_asReference((ParsingElement*)r);}
		ParsingElement_add(this, r);
		r = *(++children);
	}
	return this;
}

// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

Grammar* Grammar_new() {
	__ALLOC(Grammar, this);
	this->axiom     = NULL;
	this->skip      = NULL;
	this->elements  = NULL;
	return this;
}

// ----------------------------------------------------------------------------
//
// CONTEXT
//
// ----------------------------------------------------------------------------

Context* Context_new() {
	__ALLOC(Context, this);
	this->status    = STATUS_INIT;
	this->separator = EOL;
	this->offset    = 0;
	this->lines     = 0;
	this->head      = NULL;
	return this;
}

// ----------------------------------------------------------------------------
//
// FILE INPUT
//
// ----------------------------------------------------------------------------

/**
 * Creates a new file input with the given path and buffer size
*/
PUBLIC FileInput* FileInput_new(const char* path, unsigned int bufferSize ) {
	__ALLOC(FileInput, this);
	assert(this != NULL);
	// We open the file
	this->file = fopen(path, "r");
	if (this->file==NULL) {
		ERROR("Cannot open file: %s", path);
		__DEALLOC(this);
		return NULL;
	} else {
		// And allocate the buffer. We make sure that the buffer size is a multiple
		// of the iterated_t.
		bufferSize         = (bufferSize/sizeof(iterated_t)) * sizeof(iterated_t);
		this->bufferSize   = bufferSize;
		this->readableSize = 0;
		this->buffer       = malloc(bufferSize);
		return this;
	}
}

void FileInput_destroy(FileInput* this) {
	if (this->file != NULL) { fclose(this->file);   }
	__DEALLOC(this->buffer);
}

Context* FileInput_next( Iterator* this ) {
	// We want to know if there is at one more element
	// in the file input.
	FileInput*   input         = (FileInput*)this->input;
	char*        head          = (char*)     this->context.head;
	size_t  bytes_left_to_read = input->readableSize - (this->context.head - input->buffer);
	assert (bytes_left_to_read >= 0);
	// We check wether we have bytes left to read in the buffer. If not, we
	// need to refill it.
	if ( bytes_left_to_read == 0 ) {
		// We've reached the end of the buffer, so we need to re-create a new
		// buffer.
		size_t to_read        = input->bufferSize/sizeof(iterated_t);
		size_t read           = fread(input->buffer, sizeof(iterated_t), to_read, input->file);
		input->readableSize = read * sizeof(iterated_t);
		assert(input->readableSize % sizeof(iterated_t) == 0);
		// We we've read the size of the buffer, we'll need to refesh it
		this->context.head         = (iterated_t*) input->buffer;
		if (read == 0) {
			DEBUG("End of file reached at offset %d", this->context.offset);
			this->context.status = STATUS_ENDED;
			return &this->context;
		}
	}
	// We have enough space left in the buffer to read at least one character.
	// We increase the head, copy
	this->context.head++;
	this->context.offset++;
	if (*(this->context.head) == this->context.separator) {this->context.lines++;}
	return &this->context;
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
		this->context.head   = input->buffer;
		this->next           = FileInput_next;
		ENSURE(input->file) {};
		return TRUE;
	} else {
		return FALSE;
	}
}


void Iterator_destroy( Iterator* this ) {
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// MAIN
//
// ----------------------------------------------------------------------------

int main (int argc, char* argv[]) {
	NEW(Iterator, i);
	Iterator_open(i, "expression.txt");
	Context* context = NULL;
	assert(i != NULL);
	DEBUG("REf: %zd PAR:%zd", sizeof(Reference*), sizeof(ParsingElement*));

	Grammar* g                 = Grammar_new();

	ParsingElement* s_NUMBER   = Token_new("[0-9]+(\\.[0-9]+)?");
	ParsingElement* s_VARIABLE = Token_new("[A-Z]+");
	ParsingElement* s_OP       = Token_new("\\-|\\+|\\*");
	ParsingElement* s_Value    = Group_new( (Reference*[]) {s_NUMBER, s_VARIABLE, NULL});

	/*
	ParsingElement* s_Suffix   = Rule_new ( s_OP,     s_Value);
	ParsingElement* s_Expr     = Rule_new ( s_Value,  Reference_Many(s_Suffix) );
	*/

	while (context == NULL || context->status != STATUS_ENDED) {
		context = i->next(i);
		assert(context != NULL);
		printf("Read: %c at %d, context.status=%c\n", *(context->head), context->offset, context->status);
	}
}

// EOF
