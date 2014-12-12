PRODUCTS = parsing
SOURCES  = $(wildcard src/*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
CC       = gcc

parsing: build/parsing.o
	gcc $< -o parsing
	chmod +x parsing

clean:
	rm $(OBJECTS) $(PRODUCTS) ; true

build/%.o: src/%.c build
	$(CC) -c $< -o $@

build:
	mkdir build

# EOF
