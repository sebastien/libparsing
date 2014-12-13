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

const Match FAILURE = (Match){.status=STATUS_FAILED,  .length=0, .data=NULL, .next=NULL};

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
	return this!=NULL && ((ParsingElement*)this)->type == ParsingElement_T
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
	while (children != NULL) {
		Reference* next = children->next;
		__DEALLOC(children);
		children = next;
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

Match* ParsingElement_match( ParsingElement* this, Iterator* iterator ) {
	if (this->match) {
		return this->match(this, iterator);
	} else {
		return &FAILURE;
	}
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

Reference* Reference_new() {
	__ALLOC(Reference, this);
	this->type        = Reference_T;
	this->cardinality = CARD_SINGLE;
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

Match* Reference_match(Reference* this, Iterator* iterator) {
	// TODO
	return &FAILURE;
}

// ----------------------------------------------------------------------------
//
// TOKEN
//
// ----------------------------------------------------------------------------

ParsingElement* Token_new(const char* expr) {
	__ALLOC(Token, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->match = Token_match;
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

Match* Token_match(ParsingElement* this, Iterator* iterator) {
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
	this->match = Group_match;
	return this;
}

Match* Group_match(ParsingElement* this, Iterator* iterator){
	Reference* child = this->children;
	Match*     result;
	while (child != NULL ) {
		// FIXME: We should do a Reference_match instead
		result = ParsingElement_match(child->element, iterator);
		if (result.status == STATUS_MATCHED) {return result;}
		else                                 {child++;}
	}
	return &FAILURE;
}

// ----------------------------------------------------------------------------
//
// RULE
//
// ----------------------------------------------------------------------------

ParsingElement* Rule_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->match = Rule_match;
	return this;
}

Match* Rule_match (ParsingElement* this, Iterator* iterator){
	Reference* child  = this->children;
	Match*     result = NULL;
	Match*     last   = NULL;
	while (child != NULL ) {
		Match* current = ParsingElement_match(child->element, iterator);
		if (current != STATUS_MATCHED) {return &FAILURE;}
		if (last == NULL) {
			result = current;
			last   = current;
		} else {
			last->next = current;
			last       = current
		}
	}
	return result;
}

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
	// ParsingElement* s_Value    = Group_new(NULL);
	// 	ParsingElement_add( s_Value, ONE(s_NUMBER)   );
	// 	ParsingElement_add( s_Value, ONE(s_VARIABLE) );

	// ParsingElement* s_Suffix   = Rule_new (NULL);
	// 	ParsingElement_add( s_Suffix, ONE(s_OP)   );
	// 	ParsingElement_add( s_Suffix, ONE(s_Value) );

	// ParsingElement* s_Expr    = Rule_new (NULL);
	// 	ParsingElement_add( s_Expr, ONE (s_Value)  );
	// 	ParsingElement_add( s_Expr, MANY(s_Suffix) );

	// g->axiom = s_Expr;
	// g->skip  = s_SPACES;

	Iterator* i = Iterator_new();
	const char* path = "expression.txt";

	if (!Iterator_open(i, path)) {
		ERROR("Cannot open file: %s", path);
	} else {
		DEBUG("Opening file: %s", path)
		// Grammar_parseWithIterator( g, i );
	}
}

// EOF
