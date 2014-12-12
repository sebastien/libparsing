PRODUCTS = parsing
SOURCES  = $(wildcard src/*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
CC       = colorgcc
CFLAGS  += -g

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
