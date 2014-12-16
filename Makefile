PRODUCTS = parsing
SOURCES  = $(wildcard src/*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
CC       = colorgcc
LIBS    := libpcre
CFLAGS  += -g -std=c11 -DDEBUG_ENABLED
LDFLAGS := $(shell pkg-config --cflags --libs $(LIBS))

parsing: build/parsing.o
	gcc $< $(LDFLAGS) -o $@
	chmod +x $@

run: parsing
	./parsing

debug: parsing
	gdb ./parsing
	
experiment/%: build/%.o build/parsing.o
	gcc $< $(LDFLAGS) -o $@
	chmod +x $@

clean:
	rm $(OBJECTS) $(PRODUCTS) ; true

build:
	mkdir build

build/experiment-%.o: experiment/experiment-%.c src/parsing.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/%.c src/%.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@


# EOF
