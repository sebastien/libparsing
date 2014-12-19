PROJECT  = parsing
VERSION  = $(shell grep VERSION src/parsing.h | cut -d'"' -f2)
MAJOR    = $(shell echo $(VERSION) | cut -d. -f1)
PRODUCTS = $(PROJECT) lib$(PROJECT).so.$(VERSION)
SOURCES  = $(wildcard src/*.c)
OBJECTS  = $(SOURCES:src/%.c=build/%.o)
CC       = clang
LIBS    := libpcre
CFLAGS  += -std=c11 -g -Wall -fPIC -DDEBUG_ENABLED
LDFLAGS := -shared $(shell pkg-config --cflags --libs $(LIBS))

all: libparsing

libparsing: lib$(PROJECT).so.$(VERSION)
	
parsing: build/parsing.o
	$(CC) $< $(LDFLAGS) -o $@
	chmod +x $@

lib$(PROJECT).so.$(VERSION): build/parsing.o
	#$(CC) -shared -lpcre -Wl,-soname,lib$(PROJECT).so.$(MAJOR) -o $@ $<
	$(LD) -shared -lpcre $< -o $@

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
