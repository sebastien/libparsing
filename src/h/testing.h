#define WITH_DEBUG 1
#include "oo.h"
#include <stdio.h>

// extern int started;
//
// typedef struct {
// 	char        type;
// 	const char* name;
// 	float       value;
// } TestResult;
//
// typedef TestResult (test*) (void) test_t;
//
// TestResult test_run (test_t);

#define TEST_SUCCEED printf("[OK]\n");
#define TEST_TRUE(e)  if (e != TRUE) {printf("[ERROR] Value exected to be TRUE at %s:%d\n", __FILE__, __LINE__);}
#define TEST_FALSE(e) if (e != FALSE)  {printf("[ERROR] Value expected to be FALSE at %s:%d\n", __FILE__, __LINE__);}
