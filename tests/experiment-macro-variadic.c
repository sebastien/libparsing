#!/usr/bin/tcc -run
#include "src/oo.h"

#define COUNT VA_ARGS_COUNT
int main()
{
	printf("0 ARGS:%d\n", COUNT());
	printf("1 ARGS:%d\n", COUNT(1));
	printf("2 ARGS:%d\n", COUNT(1,2));
	printf("3 ARGS:%d\n", COUNT(1,2,3));
	printf("4 ARGS:%d\n", COUNT(1,2,3,4));
	printf("5 ARGS:%d\n", COUNT(1,2,3,4,5));
	printf("6 ARGS:%d\n", COUNT(1,2,3,4,5,6));
	printf("7 ARGS:%d\n", COUNT(1,2,3,4,5,6,7));
	printf("8 ARGS:%d\n", COUNT(1,2,3,4,5,6,7,8));
	return 0;
}

// EOF
