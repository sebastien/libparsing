#ifndef WITH_CFFI
#include <assert.h>
#include <stdlib.h>
#include "gc.h"
#endif


#define ASSERT_EXITS(r) assert (r != NULL)
#define ASSERT_REF(r)   assert(((gc_Reference*)r)->guard == 'G')
#define GC_TRANSPARENT

// -----------------------------------------------------------------------------
//
// REFERENCE API
//
// -----------------------------------------------------------------------------

/**
 * Returns the actual data managed by a reference.
*/
void* gc_Reference_data( gc_Reference* ref ) {
	if (ref == NULL) {
		return NULL;
	} else {
		return ref + sizeof(gc_Reference);
	}
}

void gc_Reference_acquire( gc_Reference* ref ) {
	ASSERT_EXITS(ref);
	ASSERT_REF(ref);
	ref->count += 1;
}

gc_Reference* gc_Reference_release( gc_Reference* ref ) {
	ASSERT_EXITS(ref);
	ASSERT_REF(ref);
	ref->count -= 1;
	if (ref->count <= 0) {
		gc_Reference_free(ref);
		return NULL;
	} else {
		return ref;
	}
}

void gc_Reference_free( gc_Reference* ref ) {
	ASSERT_EXITS(ref);
	ASSERT_REF(ref);
	assert(ref->count <= 0);
	free(ref);
}

// -----------------------------------------------------------------------------
//
// HIGH-LEVEL API
//
// -----------------------------------------------------------------------------


/**
 * Returns a reference from a given @ptr. The given pointer must have
 * be previously retrieve from @gc_new.
*/
gc_Reference* gc_ref( void* ptr ) {
	if (ptr == NULL) {
		return NULL;
	} else {
#ifdef GC_TRANSPARENT
		return ptr;
#else
		gc_Reference* ref = ptr - sizeof(gc_Reference);
		assert(ref->guard == 'R');
		return ref;
#endif
	}
}


void gc_init( gc_Reference* ref, size_t size ) {
#ifndef GC_TRANSPARENT
	ref->guard    = 'R';
	ref->size     = size;
	ref->count    = 1;
	ref->previous = NULL;
	ref->next     = NULL;
#endif
}

/**
 * Allocates a new data chunk of given @size and wrapping it
 * in a reference.
*/
void* gc_new( size_t size ) {
#ifdef GC_TRANSPARENT
	return malloc(size);
#else
	gc_Reference* res = malloc(sizeof(gc_Reference) + size);
	gc_init(res, size);
	return ((void*)res) + sizeof(gc_Reference);
#endif
}

void* gc_newBlank( size_t size ) {
#ifdef GC_TRANSPARENT
	return calloc(1, size);
#else
	gc_Reference* res  = calloc(1, sizeof(gc_Reference) + size);
	gc_init(res, size);
	return ((void*)res) + sizeof(gc_Reference);
#endif
}

/**
 * Frees a data chunk taht was previously allocated with @gc_new.
*/
void gc_free( void* ptr ) {
#ifdef GC_TRANSPARENT
	free(ptr);
#else
	gc_Reference_free (ptr - sizeof(gc_Reference));
#endif
}

void gc_acquire( void* ptr ) {
#ifndef GC_TRANSPARENT
	gc_Reference_acquire(gc_ref(ptr));
#endif
}

void gc_release( void* ptr ) {
#ifndef GC_TRANSPARENT
	gc_Reference_release(gc_ref(ptr));
#endif
}

void* gc_realloc( void* ptr, size_t size ) {
#ifdef GC_TRANSPARENT
	return realloc(ptr, size);
#else
	void* refptr         = (void*) gc_ref(ptr);
	gc_Reference* newref = (gc_Reference*)realloc(refptr, size + sizeof(gc_Reference));
	ASSERT_EXITS(newref);
	ASSERT_REF(newref);
	newref->size = size;
	return gc_Reference_data(newref);
#endif
}

char* gc_strdup(const char* s) {
#ifdef GC_TRANSPARENT
	return strdup(s);
#else
	size_t l = strlen(s) + 1;
	gc_Reference* newref = gc_new(l + 1);
	memcpy(gc_Reference_data(newref), s, l);
	return gc_Reference_data(newref);
#endif
}

void* gc_calloc(size_t count, size_t size) {
#ifdef GC_TRANSPARENT
	return calloc(count, size);
#else
	gc_Reference* newref = gc_newBlank(count * size);
	return gc_Reference_data(newref);
#endif
}
