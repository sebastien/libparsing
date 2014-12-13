PRODUCTS = parsing
SOURCES  = $(wildcard src/*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
CC       = colorgcc
CFLAGS  += -g -std=c11 -DDEBUG_ENABLED

parsing: build/parsing.o
	gcc $< -o parsing
	chmod +x parsing

clean:
	rm $(OBJECTS) $(PRODUCTS) ; true

build:
	mkdir build

build/%.o: src/%.c src/%.h src/oo.h build
	$(CC) $(CFLAGS) -c $< -o $@

# EOF
