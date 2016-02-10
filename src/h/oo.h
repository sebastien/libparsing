// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 12-Dec-2014
// Last modification : 27-Jan-2016
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
typedef char  bool;
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
#define ENSURE(v)  if (v==NULL) {printf("[!] %s\n", strerror(errno));}
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

#define DEBUG_STREAM   stderr
#define WARNING_STREAM stderr
#define ERROR_STREAM   stderr
#define LOG_STREAM     stderr

#define PUBLIC /* @public */

#ifdef DEBUG_ENABLED
#define DEBUG(msg,...)   fprintf(DEBUG_STREAM,   "--- ");fprintf(DEBUG_STREAM,   msg, __VA_ARGS__);fprintf(DEBUG_STREAM,   "\n");
#define DEBUG_IF(cond,msg,...)   if (cond) {DEBUG(msg, __VA_ARGS__);}
#define DEBUG_CODE(_) _ ;
#else
#define DEBUG(msg,...)          ;
#define DEBUG_IF(cond,msg,...)   ;
#define DEBUG_CODE(_)            ;
#endif

#ifdef TRACE_ENABLED
#define TRACE(msg,...)   fprintf(DEBUG_STREAM,   "--- ");fprintf(DEBUG_STREAM,   msg, __VA_ARGS__);fprintf(DEBUG_STREAM,   "\n");
#else
#define TRACE(msg,...)          ;
#endif

#define WARNING(msg,...) fprintf(WARNING_STREAM, "WRN ");fprintf(WARNING_STREAM, msg, __VA_ARGS__);fprintf(WARNING_STREAM, "\n");
#define ERROR(msg,...)   fprintf(WARNING_STREAM, "ERR ");fprintf(ERROR_STREAM,   msg, __VA_ARGS__);fprintf(ERROR_STREAM,   "\n");
#define LOG(msg,...)     fprintf(LOG_STREAM,     "--- ");fprintf(LOG_STREAM,     msg, __VA_ARGS__);fprintf(LOG_STREAM,     "\n");
#define LOG_IF(cond,msg,...)     if(cond){LOG(msg, __VA_ARGS__);}

#ifdef DEBUG_ENABLED
#define ASSERT(v,msg,...) if(!(v)){DEBUG(msg,__VA_ARGS__);abort();}
#else
#define ASSERT(v,msg,...) /* */
#endif

// todo: ERROR, WARNING, INFO, DEBUG
// todo: COUNTER(name, delta)
// todo: RECYCLE(value,pool), GENERATE(value,pool)

/*
 * Variadic Arguments
 * ==================
*/

// FROM: https://github.com/aeyakovenko/notes#counting-args-with-c-macros
#define VA_ARGS_COUNT(...) VA_ARGS_COUNT_(-1,##__VA_ARGS__,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0)
#define VA_ARGS_COUNT_(z,a,b,c,d,e,f,g,h,i,j,l,m,n,o,p,q,r,s,t,u,v,w,x,y,cnt,...) cnt

#define MIN(a,b) (a < b ? a : b)
#define MAX(a,b) (a > b ? a : b)

#endif
// EOF
