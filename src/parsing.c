// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 12-Dec-2014
// ----------------------------------------------------------------------------

#include "parsing.h"
#include "oo.h"

// SEE: https://en.wikipedia.org/wiki/C_data_types
// SEE: http://stackoverflow.com/questions/18329532/pcre-is-not-matching-utf8-characters
// HASH: search.h, hcreate, hsearch, etc

// ----------------------------------------------------------------------------
//
// ITERATOR
//
// ----------------------------------------------------------------------------

Iterator* Iterator_Open(const char* path) {
	NEW(Iterator,result);
	if (Iterator_open(result, path)) {
		return result;
	} else {
		Iterator_destroy(result);
		return NULL;
	}
}

Iterator* Iterator_new( void ) {
	__ALLOC(Iterator, this);
	this->status        = STATUS_INIT;
	this->separator     = EOL;
	this->buffer        = NULL;
	this->current       = NULL;
	this->offset        = 0;
	this->lines         = 0;
	this->available     = 0;
	this->length        = 0;
	this->input         = NULL;
	this->next          = NULL;
	return this;
}

bool Iterator_open( Iterator* this, const char *path ) {
	NEW(FileInput,input, path);
	assert(this->status == STATUS_INIT);
	if (input!=NULL) {
		this->input  = (void*)input;
		this->status = STATUS_PROCESSING;
		this->offset = 0;
		// We allocate a buffer that's twice the size of ITERATOR_BUFFER_AHEAD
		// so that we ensure that the current position always has ITERATOR_BUFFER_AHEAD
		// bytes ahead (if the input source has the data)
		assert(this->buffer == NULL);
		this->length  = sizeof(iterated_t) * ITERATOR_BUFFER_AHEAD * 2;
		this->buffer  = malloc(this->length + 1);
		this->current = (iterated_t*)this->buffer;
		// We make sure we have a trailing \0 sign to stop any string parsing
		// function to go any further.
		((char*)this->buffer)[this->length] = '\0';
		this->next   = FileInput_next;
		ENSURE(input->file) {};
		return TRUE;
	} else {
		return FALSE;
	}
}

void Iterator_destroy( Iterator* this ) {
	// TODO: Take care of input
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// FILE INPUT
//
// ----------------------------------------------------------------------------

FileInput* FileInput_new(const char* path ) {
	__ALLOC(FileInput, this);
	assert(this != NULL);
	// We open the file
	this->file = fopen(path, "r");
	if (this->file==NULL) {
		ERROR("Cannot open file: %s", path);
		__DEALLOC(this);
		return NULL;
	} else {
		return this;
	}
}

void FileInput_destroy(FileInput* this) {
	if (this->file != NULL) { fclose(this->file);   }
}

bool FileInput_next( Iterator* this ) {
	// We want to know if there is at one more element
	// in the file input.
	FileInput*   input         = (FileInput*)this->input;
	size_t       read          = this->current   - this->buffer;
	size_t       left          = this->available - read;
	DEBUG("FileInput_next: %zd read, %zd available / %zd length [%c]", read, this->available, this->length, this->status);
	assert (read >= 0);
	assert (left >= 0);
	assert (left  < this->length);
	// Do we have less left than the buffer ahead
	if ( left < ITERATOR_BUFFER_AHEAD && this->status != STATUS_INPUT_ENDED) {
		// We move buffer[current:] to the begining of the buffer
		memmove((void*)this->buffer, (void*)this->current, left);
		size_t to_read        = this->length - left;
		size_t read           = fread((void*)this->buffer + left, sizeof(char), to_read, input->file);
		this->available       = left + read;
		this->current         = this->buffer;
		left                  = this->available;
		if (read == 0) {
			DEBUG("End of file reached at offset %zd", this->offset);
			this->status = STATUS_INPUT_ENDED;
		}
	}
	if (left > 0) {
		// We have enough space left in the buffer to read at least one character.
		// We increase the head, copy
		this->current++;
		this->offset++;
		if (*(this->current) == this->separator) {this->lines++;}
		return TRUE;
	} else {
		return FALSE;
	}
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
	return this;
}

// ----------------------------------------------------------------------------
//
// PARSING ELEMENT
//
// ----------------------------------------------------------------------------

bool ParsingElement_Is(void *this) {
	return this!=NULL && ((ParsingElement*)this)->type == ParsingElement_T;
}

ParsingElement* ParsingElement_new(Reference* children[]) {
	__ALLOC(ParsingElement, this);
	this->type      = ParsingElement_T;
	this->id        = 0;
	this->name      = "_";
	this->config    = NULL;
	this->children  = NULL;
	this->recognize = NULL;
	this->process   = NULL;
	// if (children != NULL ) {
	// 	Reference* r = *children;
	// 	while ( r != NULL ) {
	// 		// FIXME: Make sure how memory is managed here
	// 		if (ParsingElement_is(r)) {r = ParsingElement_asReference((ParsingElement*)r);}
	// 		ParsingElement_add(this, r);
	// 		r = *(++children);
	// 	}
	// }
	return this;
}

void ParsingElement_destroy(ParsingElement* this) {
	Reference* child = this->children;
	while (child != NULL) {
		Reference* next = child->next;
		__DEALLOC(child);
		child = next;
	}
	__DEALLOC(this);
}

ParsingElement* ParsingElement_add(ParsingElement *this, Reference *child) {
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

Match* ParsingElement_recognize( ParsingElement* this, ParsingContext* context ) {
	return FAILURE;
}

Match* ParsingElement_process( ParsingElement* this, Match* match ) {
	return match;
}

// ----------------------------------------------------------------------------
//
// REFERENCE
//
// ----------------------------------------------------------------------------


bool Reference_Is(void *this) {
	return this!=NULL && ((Reference*)this)->type == Reference_T;
}

Reference* Reference_New(ParsingElement* element){
	NEW(Reference, this);
	this->element = element;
	return this;
}

Reference* Reference_new() {
	__ALLOC(Reference, this);
	this->type        = Reference_T;
	this->cardinality = CARDINALITY_SINGLE;
	this->name        = "_";
	this->element     = NULL;
	this->next        = NULL;
	return this;
}

Reference* Reference_cardinality(Reference* this, char cardinality) {
	assert(this!=NULL);
	this->cardinality = cardinality;
	return this;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {
	// TODO
	return FAILURE;
}

// ----------------------------------------------------------------------------
//
// TOKEN
//
// ----------------------------------------------------------------------------

ParsingElement* Token_new(const char* expr) {
	__ALLOC(Token, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->recognize      = Token_recognize;
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

// TODO: Implement Token_destroy and regfree

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
	// We get the current parsing context and make sure we have
	// at least TOKEN_MATCH_RANGE characters available (or the EOF). The
	// limitation here is that we don't necessarily want ot load the whole
	// file in memory, but could do it 1MB/time for instance.

	// NOTE: This means we need to pass the context
	//
	// Context_preload(context, TOKEN_MATCH_RANGE);
	//
	// regmatch_t matches[2];
	// regexec(
	//      ((TokenConfig*)this->config)->regex,
	//      context->rest,
	//      1,
	//      matches,
	//      0)
}


// ----------------------------------------------------------------------------
//
// GROUP
//
// ----------------------------------------------------------------------------

ParsingElement* Group_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->recognize = Group_recognize;
	return this;
}

Match* Group_recognize(ParsingElement* this, ParsingContext* context){
	Reference* child = this->children;
	Match*     match;
	while (child != NULL ) {
		// FIXME: We should do a Reference_recognize instead
		match = ParsingElement_recognize(child->element, context);
		if (match->status == STATUS_MATCHED)  {return match;}
		else                                 {child++;}
	}
	return FAILURE;
}

// ----------------------------------------------------------------------------
//
// RULE
//
// ----------------------------------------------------------------------------

ParsingElement* Rule_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->recognize      = Rule_recognize;
	return this;
}

Match* Rule_recognize (ParsingElement* this, ParsingContext* context){
	Reference* child  = this->children;
	Match*     result = NULL;
	Match*     last   = NULL;
	while (child != NULL ) {
		Match* current = ParsingElement_recognize(child->element, context);
		if (current->status != STATUS_MATCHED) {return FAILURE;}
		if (last == NULL) {
			result = current;
			last   = current;
		} else {
			last->next = current;
			last       = current;
		}
	}
	return result;
}

// ----------------------------------------------------------------------------
//
// PARSING STEP
//
// ----------------------------------------------------------------------------

ParsingStep* ParsingStep_new( ParsingElement* element ) {
	__ALLOC(ParsingStep, this);
	this->element   = element;
	this->step      = 0;
	this->iteration = 0;
	this->status    = STATUS_INIT;
	this->match     = (Match*)NULL;
	this->previous  = NULL;
	return this;
}

void ParsingStep_destroy( ParsingStep* this ) {
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// PARSING OFFSET
//
// ----------------------------------------------------------------------------


ParsingOffset* ParsingOffset_new( size_t offset ) {
	__ALLOC(ParsingOffset, this);
	this->offset = offset;
	this->last   = (ParsingStep*)NULL;
	this->next   = (ParsingOffset*)NULL;
	return this;
}

void ParsingOffset_destroy( ParsingOffset* this ) {
	ParsingStep* step     = this->last;
	ParsingStep* previous = NULL;
	while (step != NULL) {
		previous   = step->previous;
		ParsingStep_destroy(step);
		step       = previous;
	}
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

Match* Grammar_parseFromIterator( Grammar* this, Iterator* iterator ) {
	ParsingOffset* offset  = ParsingOffset_new(iterator->offset);
	ParsingContext context = (ParsingContext){
		.grammar  = this,
		.iterator = iterator,
		.offsets  = offset,
		.offsets  = offset,
	};
	assert(this->axiom != NULL);
	Match* match = this->axiom->recognize(this->axiom, &context);
	if (match != FAILURE) {
		LOG("Succeeded, parsed %zd", context.iterator->offset)
	} else {
		LOG("Failed, parsed %zd", context.iterator->offset)
	}
	return match;
}

//
// ----------------------------------------------------------------------------
//
// MAIN
//
// ----------------------------------------------------------------------------

int main (int argc, char* argv[]) {


	// We defined the grammar
	Grammar* g                 = Grammar_new();

	ParsingElement* s_NUMBER   = Token_new("[0-9]+(\\.[0-9]+)?");
	ParsingElement* s_VARIABLE = Token_new("[A-Z]+");
	ParsingElement* s_OP       = Token_new("\\-|\\+|\\*");
	ParsingElement* s_SPACES   = Token_new("[ ]+");

	// FIXME: This is not very elegant, but I did not really find a better
	// way. I tried passing the elements as an array, but it doesn't really
	// work.
	//
	// Alternative:
	// GROUP(s_Value) ONE(s_NUMBER) MANY(s_VARIABLE) END_GROUP
	//

	ParsingElement* s_Value    = Group_new(NULL);
		ParsingElement_add( s_Value, ONE(s_NUMBER)   );
		ParsingElement_add( s_Value, ONE(s_VARIABLE) );

	ParsingElement* s_Suffix   = Rule_new (NULL);
		ParsingElement_add( s_Suffix, ONE(s_OP)   );
		ParsingElement_add( s_Suffix, ONE(s_Value) );

	ParsingElement* s_Expr    = Rule_new (NULL);
		ParsingElement_add( s_Expr, ONE (s_Value)  );
		ParsingElement_add( s_Expr, MANY(s_Suffix) );

	g->axiom = s_Expr;
	g->skip  = s_SPACES;

	Iterator* iterator = Iterator_new();
	const char* path = "data/expression-long.txt";

	if (!Iterator_open(iterator, path)) {
		ERROR("Cannot open file: %s", path);
	} else {
		DEBUG("Opening file: %s", path)
		Grammar_parseFromIterator(g, iterator);
		// Below is a simple test on how to iterate on the file
		// int count = 0;
		// while (FileInput_next(i)) {
		// 	DEBUG("Read %c at %zd/%zd\n", *i->current, i->offset, i->available);
		// 	count += 1;
		// }
		// printf("Read %d bytes\n", count);
	}
}

// EOF
