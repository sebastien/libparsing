#ifndef __GC__
#define __GC__
#ifdef __cplusplus
extern "C" {
#endif

#define ASSERT_EXITS(r) assert (r != NULL)
#define ASSERT_REF(r)   assert(((gc_Reference*)r)->guard == 'G')
#ifdef HAS_GC
#define HAS_GC
#endif

typedef struct gc_Reference {
	char           guard;
	size_t         size;
	int            count;
	void*  previous;
	void*  next;
} gc_Reference;

// -----------------------------------------------------------------------------
//
// REFERENCE API
//
// -----------------------------------------------------------------------------

/**
 * Returns the actual data managed by a reference.
*/
void* gc_Reference_data( gc_Reference* ref );

void gc_Reference_acquire( gc_Reference* ref );

gc_Reference* gc_Reference_release( gc_Reference* ref );

void gc_Reference_free( gc_Reference* ref );

// -----------------------------------------------------------------------------
//
// HIGH-LEVEL API
//
// -----------------------------------------------------------------------------


/**
 * Returns a reference from a given @ptr. The given pointer must have
 * be previously retrieve from @gc_new.
*/
gc_Reference* gc_ref( void* ptr );


/**
 * Allocates a new data chunk of given @size and wrapping it
 * in a reference.
*/
void* gc_new( size_t size );


/**
 * Frees a data chunk taht was previously allocated with @gc_new.
*/
void gc_free( void* ptr );

// EMULATION
//
void* gc_realloc( void* ptr, size_t size );

char* gc_strdup(const char* s);

void* gc_calloc(size_t count, size_t size);

void gc_acquire( void* ptr );

void gc_release( void* ptr );

#ifdef __cplusplus
}
#endif
#endif
