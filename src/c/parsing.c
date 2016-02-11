// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 26-Jan-2016
// ----------------------------------------------------------------------------

#include "parsing.h"
#include "oo.h"

#define MATCH_STATS(m) ParsingStats_registerMatch(context->stats, this, m)
#define ANONYMOUS      "unnamed"

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
		this->capacity   = strlen(text);
		this->available  = this->capacity;
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
	this->capacity      = 0;
	this->input         = NULL;
	this->move          = NULL;
	this->freeBuffer    = FALSE;
	return this;
}

bool Iterator_open( Iterator* this, const char *path ) {
	NEW(FileInput, input, path);
	assert(this->status == STATUS_INIT);
	if (input!=NULL) {
		this->input  = (void*)input;
		this->status = STATUS_PROCESSING;
		this->offset = 0;
		// We allocate a buffer that's twice the size of ITERATOR_BUFFER_AHEAD
		// so that we ensure that the current position always has ITERATOR_BUFFER_AHEAD
		// bytes ahead (if the input source has the data)
		assert(this->buffer == NULL);
		// FIXME: Capacity should be in units, no?
		this->capacity = sizeof(iterated_t) * ITERATOR_BUFFER_AHEAD * 2;
		this->buffer   = calloc(this->capacity + 1, 1);
		assert(this->buffer != NULL);
		this->current = (iterated_t*)this->buffer;
		// We make sure we have a trailing \0 sign to stop any string parsing
		// function to go any further.
		((char*)this->buffer)[this->capacity] = '\0';
		assert(strlen(((char*)this->buffer)) == 0);
		FileInput_preload(this);
		DEBUG("Iterator_open: strlen(buffer)=%zd/%zd", strlen((char*)this->buffer), this->capacity);
		this->move   = FileInput_move;
		ENSURE(input->file);
		return TRUE;
	} else {
		return FALSE;
	}
}

bool Iterator_hasMore( Iterator* this ) {
	size_t remaining = Iterator_remaining(this);
	// DEBUG("Iterator_hasMore: %zd, offset=%zd available=%zd capacity=%zd ", remaining, this->offset, this->available, this->capacity)
	// NOTE: This used to be STATUS_ENDED, but I changed it to the actual.
	return remaining > 0;
}

size_t Iterator_remaining( Iterator* this ) {
	int buffer_offset = ((char*)this->current - this->buffer);
	// FIXME: Does not work if iterated_t is not the same as char
	int remaining = this->available - buffer_offset;
	assert(remaining >= 0);
	//DEBUG("Iterator_remaining: %d, offset=%zd available=%zd capacity=%zd", remaining, this->offset, this->available, this->capacity)
	return (size_t)remaining;
}

bool Iterator_moveTo ( Iterator* this, size_t offset ) {
	return this->move(this, offset - this->offset );
}

void Iterator_free( Iterator* this ) {
	// FIXME: Should close input file
	// TRACE("Iterator_free: %p", this)
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
	assert(this->capacity == this->available);
	if ( n == 0) {
		// --- STAYING IN PLACE -----------------------------------------------
		// We're not moving position
		DEBUG("String_move: did not move (n=%d) offset=%zd/length=%zd, available=%zd, current-buffer=%ld\n", n, this->offset, this->capacity, this->available, this->current - this->buffer);
		return TRUE;
	} else if ( n >= 0 ) {
		// --- MOVING FORWARD -------------------------------------------------
		// We're moving forward, so we want to know if there is at one more element
		// in the file input.
		size_t left = this->available - this->offset;
		// `c` is the number of elements we're actually agoing to move, which
		// is either `n` or the number of elements left.
		size_t c    = n <= left ? n : left;
		// This iterates throught the characters and counts line separators.
		while (c > 0) {
			this->current++;
			this->offset++;
			if (*(this->current) == this->separator) {this->lines++;}
			c--;
		}
		// We then store the amount of available
		left = this->available - this->offset;
		// DEBUG("String_move: moved forward by c=%zd, n=%d offset=%zd capacity=%zd, available=%zd, current-buffer=%ld", c_copy, n, this->offset, this->capacity, this->available, this->current - this->buffer);
		if (left == 0) {
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
		// We cannot backtrack further than the current offset.
		n = MAX(n, 0 - this->offset);
		// FIXME: This is a little bit brittle, we should rather use a macro
		// in the iterator itself.
		this->current    = (((ITERATION_UNIT*)this->current) + n);
		this->offset    += n;
		if (n!=0) {
			this->status  = STATUS_PROCESSING;
		}
		assert(Iterator_remaining(this) >= 0 - n);
		DEBUG("String_move: moved backwards by n=%d offset=%zd/length=%zd, available=%zd, current-buffer=%ld", n, this->offset, this->capacity, this->available, this->current - this->buffer);
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
	this->path = path;
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
	// TRACE("FileInput_free: %p", this)
	if (this->file != NULL) { fclose(this->file);   }
}

size_t FileInput_preload( Iterator* this ) {
	// We want to know if there is at one more element
	// in the file input.
	FileInput*   input         = (FileInput*)this->input;
	size_t       read          = this->current   - this->buffer;
	size_t       left          = this->available - read;
	size_t       until_eob     = this->capacity  - read;
	DEBUG("FileInput_preload: %zd read, %zd available/%zd buffer capacity [%c]", read, this->available, this->capacity, this->status);
	assert (read >= 0);
	assert (left >= 0);
	assert (left < this->capacity);
	// Do the number of bytes up until the end of the buffer is less than
	// ITERATOR_BUFFER_AHEAD, then we need to expand the the buffer and make
	// sure we have ITERATOR_BUFFER_AHEAD data, unless we reach the end of the
	// input stream.
	if ( (this->available == 0 || until_eob < ITERATOR_BUFFER_AHEAD) && this->status != STATUS_INPUT_ENDED) {
		// We move buffer[current:] to the begining of the buffer
		// FIXME: We should make sure we don't call preload each time
		// memmove((void*)this->buffer, (void*)this->current, left);
		size_t delta    = this->current - this->buffer;
		// We want to grow the buffer size by ITERATOR_BUFFER_AHEAD
		this->capacity += ITERATOR_BUFFER_AHEAD;
		// This assertion is a bit weird, but it does not hurt
		assert(this->capacity + 1 > 0);
		DEBUG("<<< FileInput: growing buffer to %zd", this->capacity + 1)
		// FIXME: Not sure that realloc is a good idea, as any previous pointer
		// to the buffer would change...
		this->buffer= realloc((void*)this->buffer, this->capacity + 1);
		assert(this->buffer != NULL);
		// We need to update the current pointer as the buffer has changed
		this->current = this->buffer + delta;
		// We make sure we add a trailing \0 to the buffer
		this->buffer[this->capacity] = '\0';
		// We want to read as much as possible so that we fill the buffer
		size_t to_read         = this->capacity - left;
		size_t read            = fread((void*)this->buffer + this->available, sizeof(iterated_t), to_read, input->file);
		this->available        += read;
		left                   += read;
		DEBUG("<<< FileInput: read %zd bytes from input, available %zd, remaining %zd", read, this->available, Iterator_remaining(this));
		assert(Iterator_remaining(this) == left);
		assert(Iterator_remaining(this) >= read);
		if (read == 0) {
			 DEBUG("FileInput_preload: End of file reached with %zd bytes available", this->available);
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
		ASSERT(this->capacity > this->offset, "FileInput_move: offset is greater than capacity (%zd > %zd)", this->offset, this->capacity)
		// We make sure that `n` is not bigger than the length of the available buffer
		n = ((int)this->capacity )+ n < 0 ? 0 - (int)this->capacity : n;
		this->current = (((char*)this->current) + n);
		this->offset += n;
		if (n!=0) {this->status  = STATUS_PROCESSING;}
		DEBUG("[<] %d%d == %zd (%zd available, %zd capacity, %zd bytes left)", ((int)this->offset) - n, n, this->offset, this->available, this->capacity, Iterator_remaining(this));
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

int Grammar_symbolsCount(Grammar* this) {
	return this->axiomCount + this->skipCount;
}

void Grammar_freeElements(Grammar* this) {
	int count = (this->axiomCount + this->skipCount);
	for (int i = 0; i < count ; i++ ) {
		Element* element = this->elements[i];
		if (ParsingElement_Is(element)) {
			ParsingElement* e = (ParsingElement*)element;
			DEBUG("Grammar_freeElements(%p):[%d/%d]->ParsingElement %p %c.%d#%s", this, i, count, element, e->type, e->id, e->name)
			ParsingElement_free(e);
		} else {
			// Reference* r = (Reference*)element;
			//DEBUG("Grammar_freeElements(%p):[%d/%d]->Reference %p.%c(%d)[%c]#%s", this, i, count, element, r->type, r->id, r->cardinality, r->name)
			// Reference_free(r);
		}
	}
	this->axiomCount = 0;
	this->skipCount  = 0;
	this->skip       = NULL;
	this->axiom      = NULL;
	this->elements   = NULL;
}

void Grammar_free(Grammar* this) {
	// TRACE("Grammar_free: %p", this)
	__DEALLOC(this);
}

// ----------------------------------------------------------------------------
//
// MATCH
//
// ----------------------------------------------------------------------------

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
	// DEBUG("Allocating match: %p", this);
	this->status    = STATUS_INIT;
	this->element   = NULL;
	this->length    = 0;
	this->offset    = 0;
	this->context   = NULL;
	this->data      = NULL;
	this->children  = NULL;
	this->next      = NULL;
	this->result    = NULL;
	return this;
}


int Match_getOffset(Match *this) {
	return (int)this->offset;
}

int Match_getLength(Match *this) {
	return (int)this->length;
}

// TODO: We might want to recycle the objects for better performance and
// fewer allocs.
void Match_free(Match* this) {
	if (this!=NULL && this!=FAILURE) {
		// We free the children
		assert(this->children != this);
		Match_free(this->children);
		// We free the next one
		assert(this->next != this);
		Match_free(this->next);
		// If the match is from a parsing element
		if (ParsingElement_Is(this->element)) {
			ParsingElement* element = ((ParsingElement*)this->element);
			// and the parsing element declared a free match function, we
			// apply it.
			if (element->freeMatch) {
				element->freeMatch(this);
			}
		}
		// We deallocate this one
		__DEALLOC(this);
	}
}

bool Match_isSuccess(Match* this) {
	return (this != NULL && this != FAILURE && this->status == STATUS_MATCHED);
}

int Match__walk(Match* this, WalkingCallback callback, int step, void* context ){
	step = callback(this, step, context);
	if (this->children != NULL && step >= 0) {
		step = Match__walk(this->children, callback, step + 1, context);
	}
	if (this->next != NULL && step >= 0) {
		step = Match__walk(this->next, callback, step + 1, context);
	}
	return step;
}


int Match__walkCounter (Element* this, int step, void* context) {
	return step;
}

int Match_countAll(Match* this) {
	return Match__walk(this, Match__walkCounter, 0, NULL);
}

// ----------------------------------------------------------------------------
//
// PARSING ELEMENT
//
// ----------------------------------------------------------------------------

bool ParsingElement_Is(void *this) {
	if (this == NULL) { return FALSE; }
	switch (((ParsingElement*)this)->type) {
		// It is not a parsing element if it is a refernence
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
//
//		case TYPE_REFERENCE:
//			return FALSE;
//		default:
//			return TRUE;
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
	// TRACE("ParsingElement_free: %p", this)
	Reference* child = this->children;
	while (child != NULL) {
		Reference* next = child->next;
		assert(Reference_Is(child));
		Reference_free(child);
		child = next;
	}
	__DEALLOC(this);
}

ParsingElement* ParsingElement_add(ParsingElement* this, Reference* child) {
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

ParsingElement* ParsingElement_clear(ParsingElement* this) {
	Reference* child = this->children;
	while ( child != NULL ) {
		assert(Reference_Is(child));
		Reference* next = child->next;
		Reference_free(child);
		child = next;
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
	TRACE("ParsingElement__walk: %4d %c %-20s [%4d]", this->id, this->type, this->name, step);
	int i = step;
	step  = callback((Element*)this, step, context);
	Reference* child = this->children;
	while ( child != NULL && step >= 0) {
		// We are sure here that the child is a reference, so we can
		// call Reference__walk directly.
		assert(Reference_Is(child));
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
	this->id          = ID_UNBOUND;
	this->cardinality = CARDINALITY_ONE;
	this->name        = "_";
	this->element     = NULL;
	this->next        = NULL;
	assert(!Reference_hasElement(this));
	assert(!Reference_hasNext(this));
	// DEBUG("Reference_new: %p, element=%p, next=%p", this, this->element, this->next);
	return this;
}

void Reference_free(Reference* this) {
	// TRACE("Reference_free: %p", this)
	// NOTE: We do not free the referenced element nor the next reference.
	// That would be the job of the grammar.
	__DEALLOC(this)
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
	TRACE("Reference__walk     : %4d %c %-20s [%4d]", this->id, this->type, this->name, step);
	step = callback((Element*)this, step, context);
	if (step >= 0) {
		step = ParsingElement__walk(this->element, callback, step + 1, context);
	}
	return step;
}

Match* Reference_recognize(Reference* this, ParsingContext* context) {
	assert(this->element != NULL);
	Match* result = FAILURE;
	Match* tail   = NULL;
	int    count  = 0;
	int    offset = context->iterator->offset;
	// If the wrapped element is a procedure, then the cardinality can only be one or optional, as a procedure does
	// not consume input.
	assert(this->element->type != TYPE_PROCEDURE || this->cardinality == CARDINALITY_ONE || this->cardinality == CARDINALITY_OPTIONAL );
	while (Iterator_hasMore(context->iterator) || this->element->type == TYPE_PROCEDURE) {
		ASSERT(this->element->recognize, "Reference_recognize: Element '%s' has no recognize callback", this->element->name);
		// We ask the element to recognize the current iterator's position
		Match* match = this->element->recognize(this->element, context);
		if (Match_isSuccess(match)) {
			DEBUG("        Reference %s#%d@%s matched at %zd-%zd", this->element->name, this->element->id, this->name, context->iterator->offset - match->length, context->iterator->offset);
			if (count == 0) {
				// If it's the first match and we're in a ONE/OPTIONAL reference, we break
				// the loop.
				result = match;
				tail   = match;
				if (this->cardinality == CARDINALITY_ONE || this->cardinality == CARDINALITY_OPTIONAL) {
					// If we have cardinality that is either 0..1 or 1, then we can exit the iteration
					// as we've recognized the reference properly.
					count += 1;
					break;
				}
			} else {
				// If we're already had a match we append the tail and update
				// the tail to be the current match
				tail->next = match;
				tail       = match;
			}
			count++;
		} else {
			DEBUG_IF(count > 0, "        Reference %s#%d@%s no more match at %zd", this->element->name, this->element->id, this->name, context->iterator->offset);
			break;
		}
	}
	DEBUG_IF(count > 0, "        Reference %s#%d@%s matched %d times out of %c",  this->element->name, this->element->id, this->name, count, this->cardinality);
	// Depending on the cardinality, we might return FAILURE, or not
	bool is_success = Match_isSuccess(result) ? TRUE : FALSE;
	switch (this->cardinality) {
		case CARDINALITY_ONE:
			break;
		case CARDINALITY_OPTIONAL:
			// For optional, we return an empty match if the match fails, which
			// will make the reference succeed.
			is_success = TRUE;
			break;
		case CARDINALITY_MANY:
			assert(count > 0 || result == FAILURE);
			break;
		case CARDINALITY_MANY_OPTIONAL:
			assert(count > 0 || result == FAILURE);
			is_success = TRUE;
			break;
		default:
			// Unsuported cardinality
			ERROR("Unsupported cardinality %c", this->cardinality);
			return MATCH_STATS(FAILURE);
	}
	if (is_success == TRUE) {
		// If we have a success, then we create a new match with the reference
		// as element. The data will be NULL, but the `child` (and actually,
		// the children) will match the cardinality and will contain parsing
		// element matches.
		int    length   = context->iterator->offset - offset;
		Match* m        = Match_Success(length, (ParsingElement*)this, context);
		// We make sure that if we had a success, that we add
		m->children     = result == FAILURE ? NULL : result;
		m->offset       = offset;
		assert(m->children == NULL || m->children->element != NULL);
		LOG_IF(context->grammar->isVerbose, "    [✓] Reference %s#%d@%s matched %d/%c times over %d-%d", this->element->name, this->element->id, this->name, count, this->cardinality, offset, offset+length)
		return MATCH_STATS(m);
	} else {
		LOG_IF(context->grammar->isVerbose, "    [!] Reference %s#%d@%s failed %d/%c times at %d", this->element->name, this->element->id, this->name, count, this->cardinality, offset);
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
	config->length       = strlen(word);
	// NOTE: As of 0.7.5 we now keep a copy of the string, as it was
	// causing problems with PyPy, hinting at potential allocation issues
	// elsewhere.
	assert(sizeof(char*) == sizeof(const char*));
	config->word         = (const char*)strdup(word);
	assert(config->length>0);
	this->config         = config;
	assert(this->config    != NULL);
	assert(this->recognize != NULL);
	return this;
}

const char* Word_word(ParsingElement* this) {
	return ((WordConfig*)this->config)->word;
}

// TODO: Implement Word_free and regfree
void Word_free(ParsingElement* this) {
	// TRACE("Word_free: %p", this)
	WordConfig* config = (WordConfig*)this->config;
	if (config != NULL) {
		// We don't have anything special to dealloc besides the config
		__DEALLOC((void*)config->word);
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
		LOG_IF(context->grammar->isVerbose, "[✓] Word %s#%d:`%s` matched %zd-%zd", this->name, this->id, ((WordConfig*)this->config)->word, context->iterator->offset - config->length, context->iterator->offset);
		return success;
	} else {
		LOG_IF(context->grammar->isVerbose, "    Word %s#%d:`%s` failed at %zd", this->name, this->id, ((WordConfig*)this->config)->word, context->iterator->offset);
		return MATCH_STATS(FAILURE);
	}
}

const char* WordMatch_group(Match* match) {
	return ((WordConfig*)((ParsingElement*)match->element)->config)->word;
}

void Word_print(ParsingElement* this) {
	WordConfig* config = (WordConfig*)this->config;
	printf("Word:%c:%s#%d<%s>\n", this->type, this->name != NULL ? this->name : ANONYMOUS, this->id, config->word);
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
	// NOTE: As of 0.7.5 we now keep a copy of the string, as it was
	// causing problems with PyPy, hinting at potential allocation issues
	// elsewhere.
	config->expr         = (const char*)strdup(expr);
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
	assert(strcmp(config->expr, expr) == 0);
	assert(strcmp(Token_expr(this), expr) == 0);
	return this;
}

const char* Token_expr(ParsingElement* this) {
	return ((TokenConfig*)this->config)->expr;
}

void Token_free(ParsingElement* this) {
	TokenConfig* config = (TokenConfig*)this->config;
	if (config != NULL) {
		// FIXME: Not sure how to free a regexp
#ifdef WITH_PCRE
		if (config->regexp != NULL) {}
		if (config->extra  != NULL) {pcre_free_study(config->extra);}
#endif
		__DEALLOC((void*)config->expr);
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
		LOG_IF(context->grammar->isVerbose, "    Token %s#%d:`%s` failed at %zd", this->name, this->id, config->expr, context->iterator->offset);
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
		LOG_IF(context->grammar->isVerbose, "[✓] Token %s#%d:`%s` matched %zd-%zd", this->name, this->id, config->expr, context->iterator->offset, context->iterator->offset + result->length);

		// We create the token match
		__ALLOC(TokenMatch, data);
		data->count    = r;
		data->groups   = (const char**)malloc(sizeof(const char*) * r);
		// NOTE: We do this here, but it's probably better to do it later
		// once the token is recognized, although this poses the problem
		// of preserving the input.
		for (int j=0 ; j<r ; j++) {
			const char* substring;
			// This function copies the data into a freshly allocated
			// substring.
			pcre_get_substring(line, vector, r, j, &(substring));
			data->groups[j] = substring;
		}
		result->data = data;
		context->iterator->move(context->iterator,result->length);
		assert (result->data != NULL);
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
	assert (index >= 0);
	assert (index < m->count);
	return m->groups[index];
}

int TokenMatch_count(Match* match) {
	assert (match                != NULL);
	assert (match->data          != NULL);
	assert (match->context       != NULL);
	assert (((ParsingElement*)(match->element))->type == TYPE_TOKEN);
	TokenMatch* m = (TokenMatch*)match->data;
	return m->count;
}

void Token_print(ParsingElement* this) {
	TokenConfig* config = (TokenConfig*)this->config;
	printf("Token:%c:%s#%d<%s>\n", this->type, this->name != NULL ? this->name : ANONYMOUS, this->id, config->expr);
}


void TokenMatch_free(Match* match) {
	TRACE("TokenMatch_free: %p", match)
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
	int        step   = 0;
	while (child != NULL ) {
		match = Reference_recognize(child, context);
		if (Match_isSuccess(match)) {
			// The first succeeding child wins
			Match* result    = Match_Success(match->length, this, context);
			result->offset   = offset;
			result->children = match;
			LOG_IF( context->grammar->isVerbose && strcmp(this->name, "_") != 0, "[✓] Group %s#%d[%d] matched %zd-%zd[%zd]", this->name, this->id, step, offset, context->iterator->offset, result->length)
			return MATCH_STATS(result);
		} else {
			// Otherwise we skip to the next child
			child  = child->next;
			step  += 1;
		}
	}
	// If no child has succeeded, the whole group fails
	LOG_IF( context->grammar->isVerbose && strcmp(this->name, "_") != 0, "[!] Group %s#%d failed at %zd-%zd, backtracking to %zd", this->name, this->id, offset, context->iterator->offset, offset)
	if (context->iterator->offset != offset ) {
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
	Match*      result    = FAILURE;
	Match*      last      = NULL;
	int         step      = 0;
	const char* step_name = NULL;
	size_t      offset    = context->iterator->offset;
	// We don't need to care wether the parsing context has more
	// data, the Reference_recognize will take care of it.
	while (child != NULL) {
		// We iterate over the children of the rule. We expect each child to
		// match, and we might skip inbetween the children to find a match.
		Match* match = Reference_recognize(child, context);
		DEBUG("Rule:%s[%d]=%s %s at %zd-%zd", this->name, step, child->element->name, (Match_isSuccess(match) ? "matched" : "failed"), (Match_isSuccess(match) ?  context->iterator->offset - match->length : context->iterator->offset), context->iterator->offset);
		if (!Match_isSuccess(match)) {
			ParsingElement* skip = context->grammar->skip;
			if (skip == NULL ) {
				// We break if we had FAILURE and there is no skip defined.
				break;
			}
			// DEBUG("Rule:Skipping with element %p", skip)
			// DEBUG("Rule:Skipping with element %c#%d", skip->type, skip->id)
			Match* skip_match    = skip->recognize(skip, context);
			int    skip_count    = 0;
			DEBUG_CODE(size_t skip_offset   = context->iterator->offset)
			while (Match_isSuccess(skip_match)){skip_match = skip->recognize(skip, context); skip_count++; }
			if (skip_count > 0) {
				// If the rule failed, we try to skip characters. We free any
				// failure match, as we won't need it anymore.
				Match_free(match);
				DEBUG("Rule:%s#%d[%d] skipped %d (%zd elements)", this->name, this->id, step, skip_count, context->iterator->offset - skip_offset);
				match = Reference_recognize(child, context);
			}
			// If we haven't matched even after the skip, then we have a failure.
			if (!Match_isSuccess(match)) {
				// We free any failure match
				Match_free(match);
				result = FAILURE;
				break;
			}
		}
		if (last == NULL) {
			// If this is the first child (ie. last == NULL), we create
			// a new match success at the original parsing offset.
			result = Match_Success(0, this, context);
			result->offset   = offset;
			result->children = last = match;
		} else {
			last = last->next = match;
		}
		// We log the step name, for debugging purposes
		step_name = child->name;
		// And we get the next child.
		child     = child->next;
		// We increment the step counter, used for debugging as well.
		step++;
	}
	if (!Match_isSuccess(result)) {
		LOG_IF( context->grammar->isVerbose && offset != context->iterator->offset && strcmp(this->name, "_") != 0, "[!] Rule %s#%d failed on step %d=%s at %zd-%zd", this->name, this->id, step, step_name == NULL ? "-" : step_name, offset, context->iterator->offset)
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
		LOG_IF( context->grammar->isVerbose && strcmp(this->name, "_") != 0, "[✓] Rule %s#%d[%d] matched %zd-%zd(%zdb)", this->name, this->id, step, offset, context->iterator->offset, result->length)
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
		// FIXME: Executing handlers is still quite problematic
		//((ProcedureCallback)(this->config))(this, context);
	}
	LOG_IF( context->grammar->isVerbose && strcmp(this->name, "_") != 0, "[✓] Procedure %s#%d executed at %zd", this->name, this->id, context->iterator->offset)
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
		// FIXME: Executing handlers is still quite problematic
		//Match* result = ((ConditionCallback)this->config)(this, context);
		Match* result = (Match*)1;
		// We support special cases where the condition can return a boolean
		if      (result == (Match*)0) { result = FAILURE; }
		else if (result == (Match*)1) { result = Match_Success(0, this, context);}
		LOG_IF(context->grammar->isVerbose &&  Match_isSuccess(result), "[✓] Condition %s#%d matched %zd-%zd", this->name, this->id, context->iterator->offset - result->length, context->iterator->offset)
		LOG_IF(context->grammar->isVerbose && !Match_isSuccess(result), "[!] Condition %s#%d failed at %zd",  this->name, this->id, context->iterator->offset)
		return  MATCH_STATS(result);
	} else {
		LOG_IF(context->grammar->isVerbose, "[✓] Condition %s#%d matched by default at %zd", this->name, this->id, context->iterator->offset)
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

iterated_t* ParsingContext_text( ParsingContext* this ) {
	return this->iterator->buffer;
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
	this->failureOffset   = 0;
	this->matchOffset     = 0;
	this->matchLength     = 0;
	this->failureElement  = NULL;
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
	// have the same start sequence (char type, int id).
	Reference* r = (Reference*)e;
	if (Match_isSuccess(m)) {
		this->successBySymbol[r->id] += 1;
		if (m->offset >= this->matchOffset) {
			this->matchOffset = m->offset;
			this->matchLength = m->length;
		}
	} else {
		this->failureBySymbol[r->id] += 1;
		// We register the deepest failure
		if(m->offset >= this->failureOffset) {
			this->failureOffset  = m->offset;
			this->failureElement = m->element;
		}
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
			LOG_IF(context->grammar->isVerbose, "Succeeded, iterator at %zd, parsed %zd bytes, %zd remaining", context->iterator->offset, context->stats->bytesRead, Iterator_remaining(context->iterator));
			this->status = STATUS_SUCCESS;
		}
	} else {
		LOG_IF(context->grammar->isVerbose, "Failed, parsed %zd bytes, %zd remaining", context->iterator->offset, Iterator_remaining(context->iterator))
		this->status = STATUS_FAILED;
	}
	return this;
}


bool ParsingResult_isFailure(ParsingResult* this) {
	return this->status == STATUS_FAILED;
}

bool ParsingResult_isPartial(ParsingResult* this) {
	return this->status == STATUS_PARTIAL;
}

bool ParsingResult_isComplete(ParsingResult* this) {
	return this->status == STATUS_SUCCESS;
}

bool ParsingResult_isSuccess(ParsingResult* this) {
	return this->status == STATUS_PARTIAL || this->status == STATUS_SUCCESS;
}

iterated_t* ParsingResult_text(ParsingResult* this) {
	return this->context->iterator->buffer;
}

size_t ParsingResult_remaining(ParsingResult* this) {
	return Iterator_remaining(this->context->iterator);
}

int ParsingResult_textOffset(ParsingResult* this) {
	int buffer_offset = this->context->iterator->current - this->context->iterator->buffer;
	return this->context->iterator->offset - buffer_offset;
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
		TRACE("Grammar__resetElementIDs: reset reference %d %s [%d]", r->id, r->name, step)
		if (r->id != ID_BINDING) {
			r->id = ID_BINDING;
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		TRACE("Grammar__resetElementIDs: reset parsing element %d %s [%d]", r->id, r->name, step)
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
		if (r->id == ID_BINDING) {
			r->id = step;
			DEBUG_IF(r->name != NULL, "[%03d] [%c] %s", r->id, r->type, r->name);
			return step;
		} else {
			return -1;
		}
	} else {
		ParsingElement * r = (ParsingElement*)e;
		if (r->id == ID_BINDING) {
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
		// We would need to free elements if they were already allocated
		if (this->elements) { free(this->elements) ; this->elements = NULL; }
		assert(this->elements == NULL);
		TRACE("Grammar_prepare: resetting element IDs %c", ' ')
		Element_walk(this->axiom, Grammar__resetElementIDs, NULL);
		if (this->skip != NULL) {
			Element_walk(this->skip, Grammar__resetElementIDs, NULL);
		}
		TRACE("Grammar_prepare: assigning new element IDs %c", ' ')
		int count = Element_walk(this->axiom, Grammar__assignElementIDs, NULL);
		this->axiomCount = count;
		if (this->skip != NULL) {
			this->skipCount = Element__walk(this->skip, Grammar__assignElementIDs, count + 1, NULL) - count;
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

ParsingResult* Grammar_parseIterator( Grammar* this, Iterator* iterator ) {
	// We make sure the grammar is prepared before we start parsing
	if (this->elements == NULL) {Grammar_prepare(this);}
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

ParsingResult* Grammar_parsePath( Grammar* this, const char* path ) {
	Iterator* iterator = Iterator_Open(path);
	if (iterator != NULL) {
		return Grammar_parseIterator(this, iterator);
	} else {
		errno = ENOENT;
		return NULL;
	}
}

ParsingResult* Grammar_parseString( Grammar* this, const char* text ) {
	Iterator* iterator = Iterator_FromString(text);
	if (iterator != NULL) {
		return Grammar_parseIterator(this, iterator);
	} else {
		errno = ENOENT;
		return NULL;
	}
}

// ----------------------------------------------------------------------------
//
// PROCESSOR
//
// ----------------------------------------------------------------------------

Processor* Processor_new() {
	__ALLOC(Processor,this);
	this->callbacksCount = 100;
	this->callbacks      = calloc(this->callbacksCount, sizeof(ProcessorCallback));
	this->fallback       = NULL;
	return this;
}

void Processor_free(Processor* this) {
	//__DEALLOC(this);
}

void Processor_register (Processor* this, int symbolID, ProcessorCallback callback ) {
	if (this->callbacksCount < (symbolID + 1)) {
		int cur_count        = this->callbacksCount;
		int new_count        = symbolID + 100;
		this->callbacks      = realloc(this->callbacks, sizeof(ProcessorCallback) * new_count);
		this->callbacksCount = new_count;
		// We zero the new values, as `realloc` does not guarantee zero data.
		while (cur_count < new_count) {
			this->callbacks[cur_count] = NULL;
			cur_count++;
		}
	}
	this->callbacks[symbolID] = callback;
}

int Processor_process (Processor* this, Match* match, int step) {
	ProcessorCallback handler = this->fallback;
	if (ParsingElement_Is(match->element)) {
		int element_id = ((ParsingElement*)match->element)->id;
		if (element_id >= 0 && element_id < this->callbacksCount) {
			handler = this->callbacks[element_id];
		}
	}
	if (handler != NULL) {
		handler (this, match);
	} else {
		Match* child = match->children;
		while (child) {
			step  = Processor_process(this, child, step);
			child = child->next;
		}
	}
	return step;
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
