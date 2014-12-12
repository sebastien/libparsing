#ifndef __OO__
#define __OO__
#define __ALLOC(T,v) T* v = (T*) malloc(sizeof(T)) ; assert (v!=NULL);
#define __DEALLOC(v) if (v!=NULL) {free(v);}
#define NEW(T,v) T* v = T##_new()
#define ENSURE(v)  if (v==NULL) {printf("[!] %s\n", strerror(errno));} else
#endif
// EOF
