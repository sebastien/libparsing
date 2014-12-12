// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 12-Dec-2014
// ----------------------------------------------------------------------------

#ifndef __OO__
#define __OO__

/**
 * == oo.h
 * -- Object-oriented Macro layer
 *
 * `oo.h` is a collection of small utility functions that make it easier to
 * have OO-style programmin in C.
 *
 * Allocation
 * ==========
*/

/**
 * :: `__ALLOC`
 *
 * Allocates an object of type `T`, binding it as `v`
 *
 * ```
 * __ALLOC(Array_Int,a) ; a->push(1);
 * ```
*/
#define bool  char
#define TRUE  1
#define FALSE 0
#define __ALLOC(T,v) T* v = (T*) malloc(sizeof(T)) ; assert (v!=NULL);

/**
 * :: `__DEALLOC`
 *
 * Deallocates a reference to an object.
 * __ALLOC(Array_Int,a) ; __DEALLOC(a);
*/
#define __DEALLOC(v) if (v!=NULL) {free(v);}

/**
 * :: `__NEW`
 *
 * Creates a new instance of object T. This implies that `T_new()` is defined.
*/
#define NEW(T,v,...) T* v = T##_new(__VA_ARGS__)

/*
 * Assertions & Error-Handling
 * ===========================
*/

/**
 * :: `ENSURE`
 *
 * Ensures that the given value is not `NULL`. If it is, then an `errno`-based
 * error will be logged.
 *
 * ```
 * ENSURE(malloc(10)) { printf("Success!"); };
 * ```
*/
#define ENSURE(v)  if (v==NULL) {printf("[!] %s\n", strerror(errno));} else
#define FAILED(v)  if (v!=NULL)

/*
 * Loggging
 * ========
 *
 * Logging is done by default on `stderr`, and features the following levels
 *
 * - `DEBUG`   for developer information
 * - `WARNING` targeted to users & developers
 * - `ERROR`   targeted to users
 *
 * Each stream can be assigned a specific file output by setting the `XXX_STREAM`
 * define.
*/

#define DEBUG_STREAM   stdout
#define WARNING_STREAM stdout
#define ERROR_STREAM   stdout

#define PUBLIC /* */
#define DEBUG(msg,...)   fprintf(DEBUG_STREAM,   "DEV ");fprintf(DEBUG_STREAM,   msg, __VA_ARGS__);fprintf(DEBUG_STREAM,   "\n");
#define WARNING(msg,...) fprintf(WARNING_STREAM, "WRN ");fprintf(WARNING_STREAM, msg, __VA_ARGS__);fprintf(WARNING_STREAM, "\n");
#define ERROR(msg,...)   fprintf(WARNING_STREAM, "ERR ");fprintf(ERROR_STREAM,   msg, __VA_ARGS__);fprintf(ERROR_STREAM,   "\n");

// todo: ERROR, WARNING, INFO, DEBUG
// todo: COUNTER(name, delta)
// todo: RECYCLE(value,pool), GENERATE(value,pool)

#endif
// EOF
