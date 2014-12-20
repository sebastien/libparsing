// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 19-Dec-2014
// ----------------------------------------------------------------------------

#include "parsing.h"
#include "oo.h"

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
	if (Iterator_open(result, path)) {
		return result;
	} else {
		Iterator_free(result);
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
	this->move          = NULL;
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
	// NOTE: This is STATUS_ENDED;
	return this->status != 'E';
}

size_t Iterator_remaining( Iterator* this ) {
	return this->available - (this->current - this->buffer);
}

bool Iterator_moveTo ( Iterator* this, size_t offset ) {
	return this->move(this, offset - this->offset );
}


void Iterator_free( Iterator* this ) {
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
		ASSERT(this->length > this->offset, "FileInput_move: offset is greater than length (%zd > %zd)", this->offset, this->length);
		// We make sure that `n` is not bigger than the length of the available buffer
		n = this->length + n < 0 ? 0 - this->length : n;
		this->current = (((char*)this->current) + n);
		this->offset += n;
		this->status  = STATUS_PROCESSING;
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

Grammar* Grammar_new() {
	__ALLOC(Grammar, this);
	this->axiom     = NULL;
	this->skip      = NULL;
	return this;
}

// ----------------------------------------------------------------------------
//
// MATCH
//
// ----------------------------------------------------------------------------

Match* Match_Empty() {
	NEW(Match,this);
	this->status = STATUS_MATCHED;
	return this;
}


Match* Match_Success(size_t length, ParsingElement* element, ParsingContext* context) {
	NEW(Match,this);
	assert( element != NULL );
	this->status  = STATUS_MATCHED;
	this->element = element;
	this->offset  = context->iterator->offset;
	this->length  = length;
	return this;
}

Match* Match_new() {
	__ALLOC(Match,this);
	this->status    = STATUS_INIT;
	this->element   = NULL;
	this->length    = 0;
	this->offset    = 0;
	this->data      = NULL;
	this->child     = NULL;
	this->next      = NULL;
	return this;
}

void Match_free(Match* this) {
	if (this!=NULL && this!=FAILURE) {__DEALLOC(this);}
}

bool Match_isSuccess(Match* this) {
	return (this != NULL && this != FAILURE && this->status == STATUS_MATCHED);
}

int Match__walk(Match* this, WalkingCallback callback, int step ){
	step = callback(this, step);
	if (this->child != NULL && step >= 0) {
		step = Match__walk(this->child, callback, step + 1);
	}
	if (this->next != NULL && step >= 0) {
		step = Match__walk(this->next, callback, step + 1);
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
	this->id        = 0;
	this->name      = "_";
	this->config    = NULL;
	this->children  = NULL;
	this->recognize = NULL;
	this->process   = NULL;
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

int ParsingElement__walk( ParsingElement* this, WalkingCallback callback, int step ) {
	step = callback((Element*)this, step);
	Reference* child = this->children;
	while ( child != NULL && step >= 0) {
		step  = Reference__walk(child, callback, step + 1);
		if (step >= 0) {
			child = child->next;
		} else {
			child = NULL;
		}
	}
	return step;
}

// ----------------------------------------------------------------------------
//
// ELEMENT
//
// ----------------------------------------------------------------------------

int Element_walk( Element* this, WalkingCallback callback ) {
	return Element__walk(this, callback, 0);
}

int Element__walk( Element* this, WalkingCallback callback, int step ) {
	assert (callback != NULL);
	if (this!=NULL) {
		if (Reference_Is(this)) {
			step = Reference__walk((Reference*)this, callback, step);
		} else if (ParsingElement_Is(this)) {
			step = ParsingElement__walk((ParsingElement*)this, callback, step);
		} else {
			// If it is neither a reference or parsing element, it is a Match
			step = Match__walk((Match*)this, callback, step);
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
	return ParsingElement_Is(element) ? Reference_New(element) : element;
}

Reference* Reference_New(ParsingElement* element){
	NEW(Reference, this);
	assert(element!=NULL);
	this->element = element;
	this->name    = element->name;
	ASSERT(element->recognize, "Reference_New: Element %s has no recognize callback", element->name);
	return this;
}

Reference* Reference_new() {
	__ALLOC(Reference, this);
	this->type        = TYPE_REFERENCE;
	this->cardinality = CARDINALITY_ONE;
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

Reference* Reference_name(Reference* this, const char* name) {
	assert(this!=NULL);
	this->name        = name;
	return this;
}

int Reference__walk( Reference* this, WalkingCallback callback, int step ) {
	step = callback((Element*)this, step);
	if (step >= 0) {
		step = ParsingElement__walk(this->element, callback, step + 1);
	}
	return step;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {
	assert(this->element != NULL);
	Match* result = FAILURE;
	Match* head;
	Match* match;
	int    count    = 0;
	while (Iterator_hasMore(context->iterator)) {
		ASSERT(this->element->recognize, "Reference_recognize: Element %s has no recognize callback", this->element->name);
		// We ask the element to recognize the current iterator's position
		match = this->element->recognize(this->element, context);
		if (Match_isSuccess(match)) {
			// DEBUG("Reference_recognize: Matched %s at %zd", this->element->name, context->iterator->offset);
			if (count == 0) {
				// If it's the first match and we're in a ONE reference
				// we force has_more to FALSE and exit the loop.
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
			break;
		}
	}
	// Depending on the cardinality, we might return FAILURE, or not
	switch (this->cardinality) {
		case CARDINALITY_ONE:
			// For single, we return the match as-is
			return result;
		case CARDINALITY_OPTIONAL:
			// For optional, we return the an empty match if
			// the match fails.
			return result == FAILURE ? Match_Empty() : result;
		case CARDINALITY_MANY:
			return count > 0 ? result : FAILURE;
		case CARDINALITY_MANY_OPTIONAL:
			return count > 0 ? result : Match_Empty();
		default:
			// Unsuported cardinality
			ERROR("Unsupported cardinality %c", this->cardinality);
			return FAILURE;
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
	return this;
}

// TODO: Implement Word_free and regfree

Match* Word_recognize(ParsingElement* this, ParsingContext* context) {
	WordConfig* config = ((WordConfig*)this->config);
	if (strncmp(config->word, context->iterator->current, config->length) == 0) {
		// NOTE: You can see here that the word actually consumes input
		// and moves the iterator.
		context->iterator->move(context->iterator, config->length);
		DEBUG("[✓] %s:%s matched at %zd", this->name, ((WordConfig*)this->config)->word, context->iterator->offset);
		return Match_Success(config->length, this, context);
	} else {
		DEBUG("    %s:%s failed at %zd", this->name, ((WordConfig*)this->config)->word, context->iterator->offset);
		return FAILURE;
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
	const char* pcre_error;
	int         pcre_error_offset = -1;
	config->expr   = expr;
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
	this->config = config;
	return this;
}

void Token_free(ParsingElement* this) {
	TokenConfig* config = (TokenConfig*)this->config;
	if (config != NULL) {
		// FIXME: Not sure how to free a regexp
		if (config->regexp != NULL) {}
		if (config->extra  != NULL) {pcre_free_study(config->extra);}
		__DEALLOC(config);
	}
	__DEALLOC(this);
}

Match* Token_recognize(ParsingElement* this, ParsingContext* context) {
	assert(this->config);
	if(this->config == NULL) {return FAILURE;}
	TokenConfig* config     = (TokenConfig*)this->config;
	// NOTE: This has to be a multiple of 3, according to `man pcre_exec`
	int vector_length = 30;
	int vector[vector_length];
	int r = pcre_exec(
		config->regexp, config->extra,     // Regex
		(char*)context->iterator->current, // Line
		context->iterator->available,      // Available data
		0,                                 // Offset
		PCRE_ANCHORED,                     // OPTIONS -- we do not skip position
		vector,                            // Vector of matching offsets
		vector_length);                    // Number of elements in the vector
	Match* result = NULL;
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
		DEBUG("    %s:%s failed at %zd", this->name, config->expr, context->iterator->offset);
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
		DEBUG("[✓] %s:%s matched at %zd", this->name, config->expr, context->iterator->offset);
		context->iterator->move(context->iterator,result->length);
		assert(Match_isSuccess(result));

		// TokenMatch* data = _ALLOC(TokenMatch);
		// data->groups     = r;
		// data->vector     = malloc(r * 3);
		// memcpy(data->vector, &vector, r * 3);
	}
	return result;
}


// FIXME: Not sure what to do exactly here, but we'd like to retrieve the group
void* Token_Group(ParsingElement* this, Match* match) {
	if (!Match_isSuccess(match)) {return NULL;}
	else {return NULL;}
	//	// PCRE contains a handy function to do the above for you:
	//	for( int j=0; j<r; j++ ) {
	//		const char *match;
	//		pcre_get_substring(line, vector, r, j, &match);
	//		printf("Match(%2d/%2d): (%2d,%2d): '%s'\n", j, r-1, vector[j*2], vector[j*2+1], match);
	//		pcre_free_substring(match);
	//	}

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
	DEBUGIF(strcmp(this->name, "_") != 0,"--- Group:%s at %zd", this->name, context->iterator->offset);
	Reference* child = this->children;
	Match*     match = NULL;
	size_t     offset = context->iterator->offset;
	while (child != NULL ) {
		match = Reference_recognize(child, context);
		if (Match_isSuccess(match)) {
			// The first succeding child wins
			Match* result = Match_Success(match->length, this, context);
			result->child = match;
			return result;
		} else {
			// Otherwise we skip to the next child
			child = child->next;
		}
	}
	// If no child has succeeded, the whole group fails
	if (context->iterator->offset != offset ) {
		DEBUGIF(strcmp(this->name, "_") != 0,"[!] %s failed backtracking to %zd", this->name, offset);
		Iterator_moveTo(context->iterator, offset);
		assert( context->iterator->offset == offset );
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
	this->type           = TYPE_RULE;
	this->recognize      = Rule_recognize;
	return this;
}

Match* Rule_recognize (ParsingElement* this, ParsingContext* context){
	DEBUGIF(strcmp(this->name, "_") != 0, "--- Rule:%s at %zd", this->name, context->iterator->offset);
	Reference* child  = this->children;
	Match*     result = NULL;
	Match*     last   = NULL;
	int        step   = 0;
	size_t     offset = context->iterator->offset;
	// We don't need to care wether the parsing context has more
	// data, the Reference_recognize will take care of it.
	while (child != NULL) {
		Match* match = Reference_recognize(child, context);
		// DEBUG("Rule:%s[%d]=%s %s at %zd", this->name, step, child->element->name, (Match_isSuccess(match) ? "matched" : "failed"), context->iterator->offset);
		if (!Match_isSuccess(match)) {
			// Match_free(match);
			ParsingElement* skip = context->grammar->skip;
			Match* skip_match    = skip->recognize(skip, context);
			int    skip_count    = 0;
			while (Match_isSuccess(skip_match)){skip_match = skip->recognize(skip, context); skip_count++; }
			if (skip_count > 0) {match = Reference_recognize(child, context);}
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
		child = child->next;
		step++;
	}
	DEBUGIF( offset != context->iterator->offset && strcmp(this->name, "_") != 0 && !Match_isSuccess(result), "[!] %s[%d] failed at %zd", this->name, step, context->iterator->offset)
	DEBUGIF( strcmp(this->name, "_") != 0 &&  Match_isSuccess(result), "[✓] %s[%d] matched at %zd", this->name, step, context->iterator->offset)
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
	return result;
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
	return Match_Success(0, this, context);
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
		DEBUGIF(Match_isSuccess(result),  "[✓] Condition %s matched at %zd", this->name, context->iterator->offset)
		DEBUGIF(!Match_isSuccess(result), "[1] Condition %s failed at %zd",  this->name, context->iterator->offset)
		return  result;
	} else {
		DEBUGIF("[✓] Condition %s matched by default at %zd", this->name, context->iterator->offset)
		Match* result = Match_Success(0, this, context);
		assert(Match_isSuccess(result));
		return  result;
	}
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
// GRAMMAR
//
// ----------------------------------------------------------------------------

int Grammar__resetElementIDs(Element* e, int step) {
	if (Reference_Is(e)) {
		Reference* r = (Reference*)e;
		if (r->id != -1) {
			r->id = -1;
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id != -1) {
			r->id = -1;
			return step;
		} else {
			return -1;
		}
	}
}

int Grammar__assignElementIDs(Element* e, int step) {
	if (Reference_Is(e)) {
		Reference* r = (Reference*)e;
		if (r->id == -1) {
			r->id = step;
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id == -1) {
			r->id = step;
			return step;
		} else {
			return -1;
		}
	}
}

void Grammar_prepare ( Grammar* this ) {
	if (this->skip!=NULL)  {
		this->skip->id = 0;
	}
	if (this->axiom!=NULL) {
		Element_walk(this->axiom, Grammar__resetElementIDs);
		Element_walk(this->axiom, Grammar__assignElementIDs);
	}
}

Match* Grammar_parseFromIterator( Grammar* this, Iterator* iterator ) {
	assert(this->axiom != NULL);
	ParsingOffset* offset  = ParsingOffset_new(iterator->offset);
	ParsingContext context = (ParsingContext){
		.grammar  = this,
		.iterator = iterator,
		.offsets  = offset,
		.offsets  = offset,
	};
	Match* match = this->axiom->recognize(this->axiom, &context);
	if (match != FAILURE) {
		if (Iterator_hasMore(context.iterator) && Iterator_remaining(context.iterator) > 0) {
			LOG("Partial success, parsed %zd bytes, %zd remaining", context.iterator->offset, Iterator_remaining(context.iterator));
		} else {
			LOG("Succeeded, parsed %zd bytes", context.iterator->offset);
		}
	} else {
		LOG("Failed, parsed %zd bytes, %zd remaining", context.iterator->offset, Iterator_remaining(context.iterator))
	}
	return match;
}

Match* Grammar_parseFromPath( Grammar* this, const char* path ) {
	Iterator* iterator = Iterator_Open(path);
	Match*    result   = Grammar_parseFromIterator(this, iterator);
	Iterator_free(iterator);
	return result;
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
