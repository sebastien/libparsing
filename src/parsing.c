// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 25-Jan-2016
// ----------------------------------------------------------------------------

#include "parsing.h"
#include "oo.h"

#define MATCH_STATS(m) ParsingStats_registerMatch(context->stats, this, m)

// SEE: https://en.wikipedia.org/wiki/C_data_types
// SEE: http://stackoverflow.com/questions/18329532/pcre-is-not-matching-utf8-characters
// HASH: search.h, hcreate, hsearch, etc

iterated_t   EOL              = '\n';
Match FAILURE_S = {
	.status = STATUS_FAILED,
	.length = 0,
	.data   = NULL,
	.next   = NULL    // NOTE: next should *always* be NULL for FAILURE
};

Match* FAILURE = &FAILURE_S;

// ----------------------------------------------------------------------------
//
// ITERATOR
//
// ----------------------------------------------------------------------------

Iterator* Iterator_Open(const char* path) {
	NEW(Iterator,result);
	result->freeBuffer = TRUE;
	if (Iterator_open(result, path)) {
		return result;
	} else {
		Iterator_free(result);
		return NULL;
	}
}

Iterator* Iterator_FromString(const char* text) {
	NEW(Iterator, this);
	if (this!=NULL) {
		this->buffer     = (iterated_t*)text;
		this->current    = (iterated_t*)text;
		this->length     = strlen(text);
		this->available  = this->length;
		this->move       = String_move;
	}
	return this;
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
	this->move          = NULL;
	this->freeBuffer    = FALSE;
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
		this->buffer  = calloc(this->length + 1, 1);
		assert(this->buffer != NULL);
		this->current = (iterated_t*)this->buffer;
		// We make sure we have a trailing \0 sign to stop any string parsing
		// function to go any further.
		((char*)this->buffer)[this->length] = '\0';
		assert(strlen(((char*)this->buffer)) == 0);
		FileInput_preload(this);
		// DEBUG("Iterator_open: strlen(buffer)=%zd/%zd", strlen((char*)this->buffer), this->length);
		this->move   = FileInput_move;
		ENSURE(input->file) {};
		return TRUE;
	} else {
		return FALSE;
	}
}

bool Iterator_hasMore( Iterator* this ) {
	// DEBUG("Iterator_hasMore: %zd, offset=%zd length=%zd available=%zd", this->length - this->offset, this->offset, this->length, this->available)
	// NOTE: This used to be STATUS_ENDED, but I changed it to the actual.
	return this->offset < this->length;
}

size_t Iterator_remaining( Iterator* this ) {
	// DEBUG("Iterator_remaining: %zd, offset=%zd length=%zd available=%zd", this->length - this->offset, this->offset, this->length, this->available)
	return (this->length - this->offset);
}

bool Iterator_moveTo ( Iterator* this, size_t offset ) {
	return this->move(this, offset - this->offset );
}

void Iterator_free( Iterator* this ) {
	// FIXME: Should close input file
	if (this->freeBuffer) {
		__DEALLOC(this->buffer);
	}
	__DEALLOC(this);

}

// ----------------------------------------------------------------------------
//
// STRING INPUT
//
// ----------------------------------------------------------------------------

bool String_move ( Iterator* this, int n ) {
	if ( n == 0) {
		// --- STAYING IN PLACE -----------------------------------------------
		// We're not moving position
		DEBUG("String_move: did not move (n=%d) offset=%zd/length=%zd, available=%zd, current-buffer=%ld\n", n, this->offset, this->length, this->available, this->current - this->buffer);
		return TRUE;
	} else if ( n >= 0 ) {
		// --- MOVING FORWARD -------------------------------------------------
		// We're moving forward, so we want to know if there is at one more element
		// in the file input.
		size_t left = this->available;
		// `c` is the number of elements we're actually agoing to move, which
		// is either `n` or the number of elements left.
		size_t c    = n <= left ? n : left;
		size_t c_copy = c;
		// This iterates throught the characters and counts line separators.
		while (c > 0) {
			this->current++;
			this->offset++;
			if (*(this->current) == this->separator) {this->lines++;}
			c--;
		}
		// We then store the amount of available
		this->available = this->length - this->offset;
		DEBUG("String_move: moved forward by c=%zd, n=%d offset=%zd length=%zd, available=%zd, current-buffer=%ld", c_copy, n, this->offset, this->length, this->available, this->current - this->buffer);
		if (this->available == 0) {
			// If we have no more available elements, then the status of
			// the stream is STATUS_ENDED
			this->status = STATUS_ENDED;
			return FALSE;
		} else {
			// Otherwise, we can go on.
			return TRUE;
		}
	} else {
		// --- BACKTRACKING ---------------------------------------------------
		// We make sure that `n` is not smaller than the length of the available buffer
		// ie. n = max(n,0 - this->available);
		n = (this->available + n) < 0 ? 0 - this->available : n;
		// FIXME: This is a little bit brittle, we should rather use a macro
		// in the iterator itself.
		this->current    = (((ITERATION_UNIT*)this->current) + n);
		this->offset    += n;
		this->available -= n;
		if (n!=0) {
			this->status  = STATUS_PROCESSING;
		}
		assert(Iterator_remaining(this) >= 0 - n);
		DEBUG("String_move: moved backwards by n=%d offset=%zd/length=%zd, available=%zd, current-buffer=%ld", n, this->offset, this->length, this->available, this->current - this->buffer);
		return TRUE;
	}
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

void FileInput_free(FileInput* this) {
	if (this->file != NULL) { fclose(this->file);   }
}

size_t FileInput_preload( Iterator* this ) {
	// We want to know if there is at one more element
	// in the file input.
	FileInput*   input         = (FileInput*)this->input;
	size_t       read          = this->current   - this->buffer;
	size_t       left          = this->available - read;
	//DEBUG("FileInput_preload: %zd read, %zd available / %zd length [%c]", read, this->available, this->length, this->status);
	assert (read >= 0);
	assert (left >= 0);
	assert (left  < this->length);
	// Do we have less left than the buffer ahead?
	if ( left < ITERATOR_BUFFER_AHEAD && this->status != STATUS_INPUT_ENDED) {
		// We move buffer[current:] to the begining of the buffer
		// FIXME: We should make sure we don't call preload each time
		// memmove((void*)this->buffer, (void*)this->current, left);
		// We realloc the memory to make sure we
		size_t delta  = this->current - this->buffer;
		this->length += ITERATOR_BUFFER_AHEAD;
		assert(this->length + 1 > 0);
		DEBUG("<<< FileInput: growing buffer to %zd", this->length + 1)
		this->buffer  = realloc((void*)this->buffer, this->length + 1);
		assert(this->buffer != NULL);
		this->current = this->buffer + delta;
		// We make sure we add a trailing \0 to the buffer
		this->buffer[this->length] = '\0';
		// We want to read as much as possible so that we fill the buffer
		size_t to_read         = this->length - left;
		size_t read            = fread((void*)this->buffer + this->available, sizeof(char), to_read, input->file);
		this->available        += read;
		left                   += read;
		DEBUG("<<< FileInput: read %zd bytes from input, available %zd, remaining %zd", read, this->available, Iterator_remaining(this));
		assert(Iterator_remaining(this) == left);
		assert(Iterator_remaining(this) >= read);
		if (read == 0) {
			// DEBUG("FileInput_preload: End of file reached with %zd bytes available", this->available);
			this->status = STATUS_INPUT_ENDED;
		}
	}
	return left;
}

bool FileInput_move   ( Iterator* this, int n ) {
	if ( n == 0) {
		// We're not moving position
		return TRUE;
	} else if ( n >= 0 ) {
		// We're moving forward, so we want to know if there is at one more element
		// in the file input.
		size_t left = FileInput_preload(this);
		if (left > 0) {
			int c = n > left ? left : n;
			// We have enough space left in the buffer to read at least one character.
			// We increase the head, copy
			while (c > 0) {
				this->current++;
				this->offset++;
				if (*(this->current) == this->separator) {this->lines++;}
				c--;
			}
			DEBUG("[>] %d+%d == %zd (%zd bytes left)", ((int)this->offset) - n, n, this->offset, left);
			if (n>left) {
				this->status = STATUS_INPUT_ENDED;
				return FALSE;
			} else {
				return TRUE;
			}
		} else {
			DEBUG("FileInput_move: end of input stream reach at %zd", this->offset);
			assert (this->status == STATUS_INPUT_ENDED || this->status == STATUS_ENDED);
			this->status = STATUS_ENDED;
			return FALSE;
		}
	} else {
		// The assert below is temporary, once we figure out when to free the input data
		// that we don't need anymore this would work.
		ASSERT(this->length > this->offset, "FileInput_move: offset is greater than length (%zd > %zd)", this->offset, this->length)
		// We make sure that `n` is not bigger than the length of the available buffer
		n = this->length + n < 0 ? 0 - this->length : n;
		this->current = (((char*)this->current) + n);
		this->offset += n;
		if (n!=0) {this->status  = STATUS_PROCESSING;}
		DEBUG("[<] %d%d == %zd (%zd available, %zd length, %zd bytes left)", ((int)this->offset) - n, n, this->offset, this->available, this->length, Iterator_remaining(this));
		assert(Iterator_remaining(this) >= 0 - n);
		return TRUE;
	}
}


// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

Grammar* Grammar_new(void) {
	__ALLOC(Grammar, this);
	this->axiom      = NULL;
	this->skip       = NULL;
	this->axiomCount = 0;
	this->skipCount  = 0;
	this->elements   = NULL;
	this->isVerbose  = FALSE;
	return this;
}

void Grammar_free(Grammar* this) {
	// FIXME: Implement me. We should get a list of all the parsing elements
	// and free them.
	/*
	Element*[] symbols = Grammar_listSymbols();
	for (int i = 0; i < (this->axiomCount + this->skipCount); i++ ) {
	}
	*/
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// MATCH
//
// ----------------------------------------------------------------------------

Match* Match_Empty(Element* element, ParsingContext* context) {
	return Match_Success(0, element, context);
}


Match* Match_Success(size_t length, Element* element, ParsingContext* context) {
	NEW(Match,this);
	assert( element != NULL );
	this->status  = STATUS_MATCHED;
	this->element = element;
	this->context = context;
	this->offset  = context->iterator->offset;
	this->length  = length;
	return this;
}

Match* Match_new(void) {
	__ALLOC(Match,this);
	this->status    = STATUS_INIT;
	this->element   = NULL;
	this->length    = 0;
	this->offset    = 0;
	this->context   = NULL;
	this->data      = NULL;
	this->child     = NULL;
	this->next      = NULL;
	return this;
}


int Match_getOffset(Match *this) {
	return (int)this->offset;
}

int Match_getLength(Match *this) {
	return (int)this->length;
}

void Match_free(Match* this) {
	if (this!=NULL && this!=FAILURE) {__DEALLOC(this);}
}

bool Match_isSuccess(Match* this) {
	return (this != NULL && this != FAILURE && this->status == STATUS_MATCHED);
}

int Match__walk(Match* this, WalkingCallback callback, int step, void* context ){
	step = callback(this, step, context);
	if (this->child != NULL && step >= 0) {
		step = Match__walk(this->child, callback, step + 1, context);
	}
	if (this->next != NULL && step >= 0) {
		step = Match__walk(this->next, callback, step + 1, context);
	}
	return step;
}

// ----------------------------------------------------------------------------
//
// PARSING ELEMENT
//
// ----------------------------------------------------------------------------

bool ParsingElement_Is(void *this) {
	if (this == NULL) { return FALSE; }
	switch (((ParsingElement*)this)->type) {
		case TYPE_ELEMENT:
		case TYPE_WORD:
		case TYPE_TOKEN:
		case TYPE_GROUP:
		case TYPE_RULE:
		case TYPE_CONDITION:
		case TYPE_PROCEDURE:
			return TRUE;
		default:
			return FALSE;
	}
}

ParsingElement* ParsingElement_new(Reference* children[]) {
	__ALLOC(ParsingElement, this);
	this->type      = TYPE_ELEMENT;
	this->id        = ID_UNBOUND;
	this->name      = "_";
	this->config    = NULL;
	this->children  = NULL;
	this->recognize = NULL;
	this->process   = NULL;
	this->freeMatch = NULL;
	if (children != NULL && *children != NULL) {
		Reference* r = Reference_Ensure(*children);
		while ( r != NULL ) {
			DEBUG("ParsingElement: %s adding child: %s", this->name, r->element->name)
			// FIXME: Make sure how memory is managed here
			ParsingElement_add(this, r);
			r = *(++children);
		}
	}
	return this;
}

void ParsingElement_free(ParsingElement* this) {
	DEBUG("ParsingElement_free: %p", this)
	Reference* child = this->children;
	while (child != NULL) {
		Reference* next = child->next;
		__DEALLOC(child);
		child = next;
	}
	__DEALLOC(this);
}

ParsingElement* ParsingElement_add(ParsingElement* this, Reference *child) {
	assert(!Reference_hasNext(child));
	assert(child->next == NULL);
	assert(child->element->recognize!=NULL);
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

Match* ParsingElement_process( ParsingElement* this, Match* match ) {
	return match;
}

ParsingElement* ParsingElement_name( ParsingElement* this, const char* name ) {
	if (this == NULL) {return this;}
	this->name = name;
	return this;
}

int ParsingElement__walk( ParsingElement* this, WalkingCallback callback, int step, void* context ) {
	int i = step;
	step  = callback((Element*)this, step, context);
	Reference* child = this->children;
	while ( child != NULL && step >= 0) {
		int j = Reference__walk(child, callback, ++i, context);
		if (j > 0) { step = i = j; }
		child = child->next;
	}
	return (step > 0) ? step : i;
}

// ----------------------------------------------------------------------------
//
// ELEMENT
//
// ----------------------------------------------------------------------------

int Element_walk( Element* this, WalkingCallback callback, void* context ) {
	return Element__walk(this, callback, 0, context);
}

int Element__walk( Element* this, WalkingCallback callback, int step, void* context ) {
	assert (callback != NULL);
	if (this!=NULL) {
		if (Reference_Is(this)) {
			step = Reference__walk((Reference*)this, callback, step, context);
		} else if (ParsingElement_Is(this)) {
			step = ParsingElement__walk((ParsingElement*)this, callback, step, context);
		} else {
			// If it is neither a reference or parsing element, it is a Match
			step = Match__walk((Match*)this, callback, step, context);
		}
	}
	return step;
}

// ----------------------------------------------------------------------------
//
// REFERENCE
//
// ----------------------------------------------------------------------------

bool Reference_Is(void * this) {
	return this!=NULL && ((Reference*)this)->type == TYPE_REFERENCE;
}

Reference* Reference_Ensure(void* elementOrReference) {
	void * element = elementOrReference;
	assert(element!=NULL);
	assert(Reference_Is(element) || ParsingElement_Is(element));
	return ParsingElement_Is(element) ? Reference_FromElement(element) : element;
}

Reference* Reference_FromElement(ParsingElement* element){
	NEW(Reference, this);
	assert(element!=NULL);
	this->element = element;
	this->name    = NULL;
	ASSERT(element->recognize, "Reference_FromElement: Element %s has no recognize callback", element->name);
	return this;
}

Reference* Reference_new(void) {
	__ALLOC(Reference, this);
	this->type        = TYPE_REFERENCE;
	this->id          = -1;
	this->cardinality = CARDINALITY_ONE;
	this->name        = "_";
	this->element     = NULL;
	this->next        = NULL;
	assert(!Reference_hasElement(this));
	assert(!Reference_hasNext(this));
	// DEBUG("Reference_new: %p, element=%p, next=%p", this, this->element, this->next);
	return this;
}

bool Reference_hasElement(Reference* this) {
	return this->element != NULL;
}

bool Reference_hasNext(Reference* this) {
	return this->next != NULL;
}

Reference* Reference_cardinality(Reference* this, char cardinality) {
	assert(this!=NULL);
	this->cardinality = cardinality;
	return this;
}

Reference* Reference_name(Reference* this, const char* name) {
	assert(this!=NULL);
	this->name        = name;
	return this;
}

int Reference__walk( Reference* this, WalkingCallback callback, int step, void* context ) {
	step = callback((Element*)this, step, context);
	if (step >= 0) {
		step = ParsingElement__walk(this->element, callback, step + 1, context);
	}
	return step;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {
	assert(this->element != NULL);
	Match* result = FAILURE;
	Match* head;
	Match* match;
	int    count    = 0;
	int    offset   = context->iterator->offset;
	// DEBUG("Reference_recognize: %s offset %d", this->element->name, offset);
	while (Iterator_hasMore(context->iterator)) {
		ASSERT(this->element->recognize, "Reference_recognize: Element %s has no recognize callback", this->element->name);
		// We ask the element to recognize the current iterator's position
		match = this->element->recognize(this->element, context);
		if (Match_isSuccess(match)) {
			// DEBUG("Reference_recognize: Matched %s at %zd-%zd", this->element->name, context->iterator->offset, context->iterator->offset + match->length);
			if (count == 0) {
				// If it's the first match and we're in a ONE reference, we break
				// the loop.
				result = match;
				head   = result;
				if (this->cardinality == CARDINALITY_ONE ) {
					break;
				}
			} else {
				// If we're already had a match we append the head and update
				// the head to be the current match
				head = head->next = match;
			}
			count++;
		} else {
			// DEBUG("Reference_recognize: Failed %s at %zd", this->element->name, context->iterator->offset);
			break;
		}
	}
	// DEBUG("Reference_recognize: Count %s at %d", this->element->name, count);
	// Depending on the cardinality, we might return FAILURE, or not
	switch (this->cardinality) {
		case CARDINALITY_ONE:
			break;
		case CARDINALITY_OPTIONAL:
			// For optional, we return an empty match if the match fails, which
			// will make the reference succeed.
			result = result == FAILURE ? Match_Empty((ParsingElement*)this, context) : result;
			break;
		case CARDINALITY_MANY:
			result = count > 0 ? result : FAILURE;
			break;
		case CARDINALITY_MANY_OPTIONAL:
			result = count > 0 ? result : Match_Empty((ParsingElement*)this, context);
			break;
		default:
			// Unsuported cardinality
			ERROR("Unsupported cardinality %c", this->cardinality);
			return MATCH_STATS(FAILURE);
	}
	if (Match_isSuccess(result)) {
		int    length   = context->iterator->offset - offset;
		Match* m        = Match_Success(length, (ParsingElement*)this, context);
		assert(result->element != NULL);
		m->child        = result;
		m->offset       = offset;
		return MATCH_STATS(m);
	} else {
		return MATCH_STATS(FAILURE);
	}
}

// ----------------------------------------------------------------------------
//
// WORD
//
// ----------------------------------------------------------------------------

ParsingElement* Word_new(const char* word) {
	__ALLOC(WordConfig, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->type           = TYPE_WORD;
	this->recognize      = Word_recognize;
	assert(word != NULL);
	config->word         = word;
	config->length       = strlen(word);
	assert(config->length>0);
	this->config         = config;
	assert(this->config    != NULL);
	assert(this->recognize != NULL);
	return this;
}

// TODO: Implement Word_free and regfree
void Word_free(ParsingElement* this) {
	WordConfig* config = (WordConfig*)this->config;
	if (config != NULL) {
		// We don't have anything special to dealloc besides the config
		__DEALLOC(config);
	}
	__DEALLOC(this);
}

Match* Word_recognize(ParsingElement* this, ParsingContext* context) {
	WordConfig* config = ((WordConfig*)this->config);
	if (strncmp(config->word, context->iterator->current, config->length) == 0) {
		// NOTE: You can see here that the word actually consumes input
		// and moves the iterator.
		Match* success = MATCH_STATS(Match_Success(config->length, this, context));
		size_t offset = context->iterator->offset;
		ASSERT(config->length > 0, "Word: %s configuration length == 0", config->word)
		context->iterator->move(context->iterator, config->length);
		LOG_IF(context->grammar->isVerbose, "Moving iterator from %zd to %zd", offset, context->iterator->offset);
		LOG_IF(context->grammar->isVerbose, "[✓] %s:%s matched %zd-%zd", this->name, ((WordConfig*)this->config)->word, context->iterator->offset - config->length, context->iterator->offset);
		return success;
	} else {
		LOG_IF(context->grammar->isVerbose, "    %s:%s failed at %zd", this->name, ((WordConfig*)this->config)->word, context->iterator->offset);
		return MATCH_STATS(FAILURE);
	}
}

// ----------------------------------------------------------------------------
//
// TOKEN
//
// ----------------------------------------------------------------------------

ParsingElement* Token_new(const char* expr) {
	__ALLOC(TokenConfig, config);
	ParsingElement* this = ParsingElement_new(NULL);
	this->type           = TYPE_TOKEN;
	this->recognize      = Token_recognize;
	this->freeMatch      = TokenMatch_free;
	config->expr   = expr;
#ifdef WITH_PCRE
	const char* pcre_error;
	int         pcre_error_offset = -1;
	config->regexp = pcre_compile(expr, PCRE_UTF8, &pcre_error, &pcre_error_offset, NULL);
	if (pcre_error != NULL) {
		ERROR("Token: cannot compile regular expression `%s` at %d: %s", expr, pcre_error_offset, pcre_error);
		__DEALLOC(config);
		__DEALLOC(this);
		return NULL;
	}
	config->extra = pcre_study(config->regexp, 0, &pcre_error);
	if (pcre_error != NULL) {
		ERROR("Token: cannot optimize regular expression `%s` at %d: %s", expr, pcre_error_offset, pcre_error);
		__DEALLOC(config);
		__DEALLOC(this);
		return NULL;
	}
#endif
	this->config = config;
	return this;
}

void Token_free(ParsingElement* this) {
	TokenConfig* config = (TokenConfig*)this->config;
	if (config != NULL) {
		// FIXME: Not sure how to free a regexp
#ifdef WITH_PCRE
		if (config->regexp != NULL) {}
		if (config->extra  != NULL) {pcre_free_study(config->extra);}
#endif
		__DEALLOC(config);
	}
	__DEALLOC(this);
}

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
	assert(this->config);
	if(this->config == NULL) {return FAILURE;}
	TokenConfig* config     = (TokenConfig*)this->config;
	Match* result           = NULL;
#ifdef WITH_PCRE
	// NOTE: This has to be a multiple of 3, according to `man pcre_exec`
	int vector_length = 30;
	int vector[vector_length];
	const char* line = (const char*)context->iterator->current;
	// SEE: http://www.mitchr.me/SS/exampleCode/AUPG/pcre_example.c.html
	int r = pcre_exec(
		config->regexp, config->extra,     // Regex
		line,                              // Line
		context->iterator->available,      // Available data
		0,                                 // Offset
		  PCRE_ANCHORED                    // OPTIONS -- we do not skip position
		| PCRE_NO_UTF8_CHECK               // These following one are necessary
		| PCRE_NO_UTF16_CHECK              // for good performance, or the whole
		| PCRE_NO_UTF32_CHECK,             // string will be checked at each exec.
		vector,                            // Vector of matching offsets
		vector_length);                    // Number of elements in the vector
	if (r <= 0) {
		// DEBUG("Token: %s FAILED on %s", config->expr, context->iterator->buffer);
		switch(r) {
			case PCRE_ERROR_NOMATCH      : result = FAILURE;                                                        break;
			case PCRE_ERROR_NULL         : ERROR("Token:%s Something was null", config->expr);                      break;
			case PCRE_ERROR_BADOPTION    : ERROR("Token:%s A bad option was passed", config->expr);                 break;
			case PCRE_ERROR_BADMAGIC     : ERROR("Token:%s Magic number bad (compiled re corrupt?)", config->expr); break;
			case PCRE_ERROR_UNKNOWN_NODE : ERROR("Token:%s Something kooky in the compiled re", config->expr);      break;
			case PCRE_ERROR_NOMEMORY     : ERROR("Token:%s Ran out of memory", config->expr);                       break;
			default                      : ERROR("Token:%s Unknown error", config->expr);                           break;
		};
		LOG_IF(context->grammar->isVerbose, "    %s:%s failed at %zd", this->name, config->expr, context->iterator->offset);
	} else {
		if(r == 0) {
			ERROR("Token: %s many substrings matched\n", config->expr);
			// Set rc to the max number of substring matches possible.
			// FIMXE: Not sure why we're doing 3 here, but it's what is
			// state in the doc
			// `ovecsize     Number of elements in the vector (a multiple of 3)`
			// in `man pcre_exec`.
			r = vector_length / 3;
		}
		// FIXME: Make sure it is the length and not the end offset
		result           = Match_Success(vector[1], this, context);
		LOG_IF(context->grammar->isVerbose, "[✓] %s:%s matched %zd-%zd", this->name, config->expr, context->iterator->offset, context->iterator->offset + result->length);

		// We create the token match
		__ALLOC(TokenMatch, data);

		data->count    = r;
		data->groups   = (const char**)malloc(sizeof(const char*) * r);
		// NOTE: We do this here, but it's probably better to do it later
		// once the token is recognized, although this poses the problem
		// of preserving the input.
		for (int j=0 ; j<r ; j++) {
			const char* substring;
			pcre_get_substring(line, vector, r, j, &(substring));
			data->groups[j] = substring;
		}
		result->data = data;
		context->iterator->move(context->iterator,result->length);
		assert(Match_isSuccess(result));
	}
#endif
	return MATCH_STATS(result);
}

const char* TokenMatch_group(Match* match, int index) {
	assert (match                != NULL);
	assert (match->data          != NULL);
	assert (match->context       != NULL);
	assert (((ParsingElement*)(match->element))->type == TYPE_TOKEN);
	TokenMatch* m = (TokenMatch*)match->data;
	assert (index - m->count);
	return m->groups[index];
}

void TokenMatch_free(Match* match) {
	assert (match                != NULL);
	assert (match->data          != NULL);
	assert (match->context       != NULL);
	assert (((ParsingElement*)(match->element))->type == TYPE_TOKEN);
	TokenMatch* m = (TokenMatch*)match->data;
#ifdef WITH_PCRE
	if (m != NULL ) {
		for (int j=0 ; j<m->count ; j++) {
			pcre_free_substring(m->groups[j]);
		}
	}
#endif
}

// ----------------------------------------------------------------------------
//
// GROUP
//
// ----------------------------------------------------------------------------

ParsingElement* Group_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->type           = TYPE_GROUP;
	this->recognize      = Group_recognize;
	return this;
}

Match* Group_recognize(ParsingElement* this, ParsingContext* context){
	LOG_IF(context->grammar->isVerbose && strcmp(this->name, "_") != 0,"--- Group:%s at %zd", this->name, context->iterator->offset);
	Reference* child = this->children;
	Match*     match = NULL;
	size_t     offset = context->iterator->offset;
	while (child != NULL ) {
		match = Reference_recognize(child, context);
		if (Match_isSuccess(match)) {
			// The first succeding child wins
			Match* result = Match_Success(match->length, this, context);
			result->child = match;
			return MATCH_STATS(result);
		} else {
			// Otherwise we skip to the next child
			child = child->next;
		}
	}
	// If no child has succeeded, the whole group fails
	if (context->iterator->offset != offset ) {
		LOG_IF(context->grammar->isVerbose && strcmp(this->name, "_") != 0,"[!] %s failed backtracking to %zd", this->name, offset);
		Iterator_moveTo(context->iterator, offset);
		assert( context->iterator->offset == offset );
	}
	return MATCH_STATS(FAILURE);
}

// ----------------------------------------------------------------------------
//
// RULE
//
// ----------------------------------------------------------------------------

ParsingElement* Rule_new(Reference* children[]) {
	ParsingElement* this = ParsingElement_new(children);
	this->type           = TYPE_RULE;
	this->recognize      = Rule_recognize;
	// DEBUG("Rule_new: %p", this)
	return this;
}

Match* Rule_recognize (ParsingElement* this, ParsingContext* context){
	LOG_IF(context->grammar->isVerbose && strcmp(this->name, "_") != 0, "--- Rule:%s at %zd", this->name, context->iterator->offset);
	Reference* child  = this->children;
	// An empty rule will fail. Not sure if this is the right thing to do, but
	// if we don't set the result, it will return NULL and break assertions
	Match*     result = FAILURE;
	Match*     last   = NULL;
	int        step   = 0;
	const char*   step_name = NULL;
	size_t     offset = context->iterator->offset;
	// We don't need to care wether the parsing context has more
	// data, the Reference_recognize will take care of it.
	while (child != NULL) {
		Match* match = Reference_recognize(child, context);
		// DEBUG("Rule:%s[%d]=%s %s at %zd-%zd", this->name, step, child->element->name, (Match_isSuccess(match) ? "matched" : "failed"), (Match_isSuccess(match) ?  context->iterator->offset - match->length : context->iterator->offset), context->iterator->offset);
		if (!Match_isSuccess(match)) {
			// Match_free(match);
			ParsingElement* skip = context->grammar->skip;
			Match* skip_match    = skip->recognize(skip, context);
			int    skip_count    = 0;
			size_t skip_offset   = context->iterator->offset;
			while (Match_isSuccess(skip_match)){skip_match = skip->recognize(skip, context); skip_count++; }
			if (skip_count > 0) {
				DEBUG("Rule:%s[%d] skipped %d (%zd elements)", this->name, step, skip_count, context->iterator->offset - skip_offset);
				match = Reference_recognize(child, context);
			}
			// If we haven't matched even after the skip
			if (!Match_isSuccess(match)) {
				// Match_free(match);
				result = FAILURE;
				break;
			}
		}
		if (last == NULL) {
			result = Match_Success(0, this, context);
			result->child = last = match;
		} else {
			last = last->next = match;
		}
		step_name = child->name;
		child = child->next;
		step++;
	}
	LOG_IF( context->grammar->isVerbose && offset != context->iterator->offset && strcmp(this->name, "_") != 0 && !Match_isSuccess(result), "[!] %s#%d(%s) failed at %zd", this->name, step, step_name == NULL ? "-" : step_name, context->iterator->offset)
	LOG_IF( context->grammar->isVerbose && strcmp(this->name, "_") != 0 &&  Match_isSuccess(result), "[✓] %s[%d] matched %zd-%zd", this->name, step, context->iterator->offset - result->length, context->iterator->offset)
	if (!Match_isSuccess(result)) {
		// Match_free(result);
		// If we had a failure, then we backtrack the iterator
		if (offset != context->iterator->offset) {
			DEBUG( "... backtracking to %zd", offset)
			Iterator_moveTo(context->iterator, offset);
			assert( context->iterator->offset == offset );
		}
	} else {
		// In case of a success, we update the length based on the last
		// match.
		result->length = last->offset - result->offset + last->length;
	}
	return MATCH_STATS(result);
}

// ----------------------------------------------------------------------------
//
// PROCEDURE
//
// ----------------------------------------------------------------------------

ParsingElement* Procedure_new(ProcedureCallback c) {
	ParsingElement* this = ParsingElement_new(NULL);
	this->type      = TYPE_PROCEDURE;
	this->config    = c;
	this->recognize = Procedure_recognize;
	return this;
}

Match*  Procedure_recognize(ParsingElement* this, ParsingContext* context) {
	if (this->config != NULL) {
		((ProcedureCallback)(this->config))(this, context);
	}
	return MATCH_STATS(Match_Success(0, this, context));
}

// ----------------------------------------------------------------------------
//
// CONDITION
//
// ----------------------------------------------------------------------------

ParsingElement* Condition_new(ConditionCallback c) {
	ParsingElement* this = ParsingElement_new(NULL);
	this->type      = TYPE_CONDITION;
	this->config    = c;
	this->recognize = Condition_recognize;
	return this;
}

Match*  Condition_recognize(ParsingElement* this, ParsingContext* context) {
	if (this->config != NULL) {
		Match* result = ((ConditionCallback)this->config)(this, context);
		LOG_IF(context->grammar->isVerbose &&  Match_isSuccess(result), "[✓] Condition %s matched %zd-%zd", this->name, context->iterator->offset - result->length, context->iterator->offset)
		LOG_IF(context->grammar->isVerbose && !Match_isSuccess(result), "[1] Condition %s failed at %zd",  this->name, context->iterator->offset)
		return  MATCH_STATS(result);
	} else {
		LOG_IF(context->grammar->isVerbose, "[✓] Condition %s matched by default at %zd", this->name, context->iterator->offset)
		Match* result = Match_Success(0, this, context);
		assert(Match_isSuccess(result));
		return  MATCH_STATS(result);
	}
}

// ----------------------------------------------------------------------------
//
// PARSING STEP
//
// ----------------------------------------------------------------------------

ParsingStep* ParsingStep_new( ParsingElement* element ) {
	__ALLOC(ParsingStep, this);
	assert(element != NULL);
	this->element   = element;
	this->step      = 0;
	this->iteration = 0;
	this->status    = STATUS_INIT;
	this->match     = (Match*)NULL;
	this->previous  = NULL;
	return this;
}

void ParsingStep_free( ParsingStep* this ) {
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

void ParsingOffset_free( ParsingOffset* this ) {
	ParsingStep* step     = this->last;
	ParsingStep* previous = NULL;
	while (step != NULL) {
		previous   = step->previous;
		ParsingStep_free(step);
		step       = previous;
	}
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// PARSING CONTEXT
//
// ----------------------------------------------------------------------------

ParsingContext* ParsingContext_new( Grammar* g, Iterator* iterator ) {
	__ALLOC(ParsingContext, this);
	assert(g);
	assert(iterator);
	this->grammar  = g;
	this->iterator = iterator;
	this->stats    = ParsingStats_new();
	ParsingStats_setSymbolsCount(this->stats, g->axiomCount + g->skipCount);
	this->offsets  = NULL;
	this->current  = NULL;
	return this;
}

void ParsingContext_free( ParsingContext* this ) {
	if (this!=NULL) {
		Iterator_free(this->iterator);
		ParsingStats_free(this->stats);
		__DEALLOC(this);
	}
}

// ----------------------------------------------------------------------------
//
// PARSING STATS
//
// ----------------------------------------------------------------------------

ParsingStats* ParsingStats_new(void) {
	__ALLOC(ParsingStats,this);
	this->bytesRead = 0;
	this->parseTime = 0;
	this->successBySymbol = NULL;
	this->failureBySymbol = NULL;
	return this;
}

void ParsingStats_free(ParsingStats* this) {
	if (this != NULL) {
		__DEALLOC(this->successBySymbol);
		__DEALLOC(this->failureBySymbol);
	}
	__DEALLOC(this);
}

void ParsingStats_setSymbolsCount(ParsingStats* this, size_t t) {
	__DEALLOC(this->successBySymbol);
	__DEALLOC(this->failureBySymbol);
	this->successBySymbol = calloc(sizeof(size_t), t);
	this->failureBySymbol = calloc(sizeof(size_t), t);
	this->symbolsCount    = t;
}

Match* ParsingStats_registerMatch(ParsingStats* this, Element* e, Match* m) {
	// We can convert ParsingElements to Reference and vice-versa as they
	// have the same start sequence (cart type, int id).
	Reference* r = (Reference*)e;
	if (Match_isSuccess(m)) {
		this->successBySymbol[r->id] += 1;
	} else {
		this->failureBySymbol[r->id] += 1;
	}
	return m;
}

// ----------------------------------------------------------------------------
//
// PARSING RESULT
//
// ----------------------------------------------------------------------------

ParsingResult* ParsingResult_new(Match* match, ParsingContext* context) {
	__ALLOC(ParsingResult,this);
	assert(match != NULL);
	assert(context != NULL);
	assert(context->iterator != NULL);
	this->match   = match;
	this->context = context;
	if (match != FAILURE) {
		if (Iterator_hasMore(context->iterator) && Iterator_remaining(context->iterator) > 0) {
			LOG_IF(context->grammar->isVerbose, "Partial success, parsed %zd bytes, %zd remaining", context->iterator->offset, Iterator_remaining(context->iterator));
			this->status = STATUS_PARTIAL;
		} else {
			LOG_IF(context->grammar->isVerbose, "Succeeded, iterator at %zd, parsed %zd bytes", context->iterator->offset, context->stats->bytesRead);
			this->status = STATUS_SUCCESS;
		}
	} else {
		LOG_IF(context->grammar->isVerbose, "Failed, parsed %zd bytes, %zd remaining", context->iterator->offset, Iterator_remaining(context->iterator))
		this->status = STATUS_FAILED;
	}
	return this;
}

void ParsingResult_free(ParsingResult* this) {
	if (this != NULL) {
		Match_free(this->match);
		ParsingContext_free(this->context);
	}
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// GRAMMAR
//
// ----------------------------------------------------------------------------

int Grammar__resetElementIDs(Element* e, int step, void* nothing) {
	if (Reference_Is(e)) {
		Reference* r = (Reference*)e;
		if (r->id != ID_BINDING) {
			r->id = ID_BINDING;
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id != ID_BINDING) {
			r->id = ID_BINDING;
			return step;
		} else {
			return -1;
		}
	}
}

int Grammar__assignElementIDs(Element* e, int step, void* nothing) {
	if (Reference_Is(e)) {
		Reference* r = (Reference*)e;
		if (r->id == -1) {
			r->id = step;
			DEBUG_IF(r->name != NULL, "[%03d] [%c] %s", r->id, r->type, r->name);
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id == -1) {
			r->id = step;
			DEBUG_IF(r->name != NULL, "[%03d] [%c] %s", r->id, r->type, r->name);
			return step;
		} else {
			return -1;
		}
	}
}

int Grammar__registerElement(Element* e, int step, void* grammar) {
	Reference* r  = (Reference*)e;
	Grammar*   g  = (Grammar*)grammar;
	Element*   ge = g->elements[r->id];
	if (ge == NULL) {
		g->elements[r->id] = e;
		return step;
	} else {
		return -1;
	}
}

void Grammar_prepare ( Grammar* this ) {
	if (this->skip!=NULL)  {
		this->skip->id = 0;
	}
	if (this->axiom!=NULL) {
		Element_walk(this->axiom, Grammar__resetElementIDs, NULL);
		if (this->skip != NULL) {
			Element_walk(this->skip, Grammar__resetElementIDs, NULL);
		}
		int count = Element_walk(this->axiom, Grammar__assignElementIDs, NULL);
		this->axiomCount = count;
		if (this->skip != NULL) {
			this->skipCount = Element__walk(this->skip, Grammar__assignElementIDs, count, NULL) - count;
		}
		// Now we register the elements
		__DEALLOC(this->elements);
		this->elements = calloc( sizeof(Element*), this->skipCount + this->axiomCount);
		count = Element_walk(this->axiom, Grammar__registerElement, this);
		if (this->skip != NULL) {
			Element__walk(this->skip, Grammar__registerElement, count, this);
		}
	}
}

ParsingResult* Grammar_parseFromIterator( Grammar* this, Iterator* iterator ) {
	assert(this->axiom != NULL);
	// ParsingOffset*  offset  = ParsingOffset_new(iterator->offset);
	ParsingContext* context = ParsingContext_new(this, iterator);
	assert(this->axiom->recognize != NULL);
	clock_t t1  = clock();
	Match* match = this->axiom->recognize(this->axiom, context);
	context->stats->parseTime = ((double)clock() - (double)t1) / CLOCKS_PER_SEC;
	context->stats->bytesRead = iterator->offset;
	return ParsingResult_new(match, context);
}

ParsingResult* Grammar_parseFromPath( Grammar* this, const char* path ) {
	Iterator* iterator = Iterator_Open(path);
	if (iterator != NULL) {
		return Grammar_parseFromIterator(this, iterator);
	} else {
		errno = ENOENT;
		return NULL;
	}
}

ParsingResult* Grammar_parseFromString( Grammar* this, const char* text ) {
	printf("Grammar_parseFromString: %s\n", text);
	Iterator* iterator = Iterator_FromString(text);
	if (iterator != NULL) {
		return Grammar_parseFromIterator(this, iterator);
	} else {
		errno = ENOENT;
		return NULL;
	}
}

// ----------------------------------------------------------------------------
//
// MAIN
//
// ----------------------------------------------------------------------------

void Utilities_indent( ParsingElement* this, ParsingContext* context ) {
	//int depth = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	//ParsingContext_setVariable("indent", depth + 1,     sizeof(int));
}

void Utilities_dedent( ParsingElement* this, ParsingContext* context ) {
	//int depth = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	//ParsingContext_setVariable("indent", depth - 1,     sizeof(int));
}

Match* Utilites_checkIndent( ParsingElement *this, ParsingContext* context ) {
	// Variable tabs = ParsingContext_getVariable("tabs", NULL, sizeof(int));
	// // TokenMatch_group(0)
	// int depth     = ParsingContext_getVariable("indent", 0, sizeof(int)).asInt;
	// if (depth != tabs_count) {
	// 	return FAILURE;
	// } else {
	// 	return Match_Success();
	// }
	return Match_Success(0, this, context);
}

// EOF
