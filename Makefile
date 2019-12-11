# -----------------------------------------------------------------------------
#
# C+Python Project Makefile
# =========================
#
# Updated: 2016-11-15
# Author:  FFunction <ffctn.com>
#
# -----------------------------------------------------------------------------#
# NOTE: To do profiling, use operf & opreport

# === CONFIGURATION ===========================================================

PROJECT        :=parsing
PYMODULE       :=lib$(PROJECT)
FEATURES       :=pcre fortify gc
ALL_FEATURES   :=pcre memcheck debug trace fortify gc assert

# === FEATURES ================================================================

LIBS=
ifneq (,$(findstring pcre,$(FEATURES)))
	LIBS +=libpcre
endif
ifneq (,$(findstring python2,$(FEATURES)))
	LIBS +=python2
	CFLAGS+=-DWITH_PYTHON
	PYTHON=python2
endif
ifneq (,$(findstring python3,$(FEATURES)))
	LIBS +=python3
	CFLAGS+=-DWITH_PYTHON
	PYTHON=python3
endif
ifeq (,$(findstring assert,$(FEATURES)))
	CFLAGS+=-DNDEBUG
endif
ifneq (,$(findstring debug,$(FEATURES)))
	CFLAGS+=-Og
else
	CFLAGS+=-O3
endif
ifneq (,$(findstring fortify,$(FEATURES)))
	CFLAGS+= -U_FORTIFY_SOURCE -fstack-protector-all
endif

# === PATHS ===================================================================

BUILD          =.build
DIST           =dist
SOURCES        =src
TESTS          =test

# === TOOLS ===================================================================

PYTHON         ?=python3.7

# === SOURCES =================================================================

SOURCES_C      =$(wildcard $(SOURCES)/c/*.c)
SOURCES_H      =$(wildcard $(SOURCES)/h/*.h)
SOURCES_PY     =$(wildcard $(SOURCES)/py/*.py) $(wildcard $(SOURCES)/py/*/*.py)
TESTS_C        =$(wildcard $(TESTS)/*.c)
TESTS_PY       =$(wildcard $(TESTS)/*.py)

# === BUILD FILES =============================================================

BUILD_SOURCES_O =$(SOURCES_C:$(SOURCES)/c/%.c=$(BUILD)/%.o)
BUILD_TESTS_O   =$(TESTS_C:$(TESTS)/%.c=$(BUILD)/%.o)
BUILD_O         =$(BUILD_SOURCES_O) $(BUILD_TESTS_O)
BUILD_PY_SO        =$(SOURCES)/python/lib$(PROJECT)/lib$(PROJECT).so   \
                 $(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).so  \

BUILD_PY_FFI       =$(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).ffi \
                 $(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).c
BUILD_ALL       =$(BUILD_O) $(BUILD_PY_SO) $(BUILD_PY_FFI)

# === DIST FILES ==============================================================

DIST_TESTS    = $(TESTS_C:$(TESTS)/%.c=$(DIST)/%)
DIST_BIN      = $(DIST_TESTS)
DIST_SO       = $(DIST)/lib$(PROJECT).so $(DIST)/lib$(PROJECT).so.$(VERSION) 
DIST_ALL      = $(DIST_BIN) $(DIST_SO)
PRODUCTS      = $(DIST_ALL)

# === COMPILER FILES ==========================================================

CC       ?= gcc
CFEATURES:=$(shell echo $(FEATURES:%=-DWITH_%) | tr a-z A-Z)
CFLAGS   +=$(shell pkg-config --cflags $(LIBS))
CFLAGS   +=-I$(SOURCES)/h -Wall -fPIC $(CFEATURES) -g #-DMEMCHECK_ENABLED -pg # -DDEBUG_ENABLED -DTRACE_ENABLED
LDFLAGS  +=$(shell pkg-config --cflags --libs $(LIBS))

# === DEPENDENCY MANAGEMENT ===================================================
# SEE: http://make.mad-scientist.net/papers/advanced-auto-dependency-generation/

DEPDIR  := .build/d
$(shell mkdir -p $(DEPDIR) >/dev/null)
DEPFLAGS    = -MT $@ -MMD -MP -MF $(DEPDIR)/$*.Td
COMPILE.c   = $(CC)  $(DEPFLAGS) $(CFLAGS)  $(TARGET_ARCH) -c
POSTCOMPILE = mv -f $(DEPDIR)/$*.Td $(DEPDIR)/$*.d

# === META ====================================================================

VERSION        :=$(shell grep VERSION $(SOURCES)/h/parsing.h | cut -d'"' -f2)
MAJOR          :=$(shell echo $(VERSION) | cut -d. -f1)

# === HELPERS =================================================================

YELLOW           =`tput setaf 11`
GREEN            =`tput setaf 10`
CYAN             =`tput setaf 14`
RED              =`tput setaf 1`
GRAY             =`tput setaf 7`
RESET            =`tput sgr0`

TIMESTAMP       :=$(shell date +'%F')
BUILD_ID        :=$(shell git rev-parse --verify HEAD)
MAKEFILE_PATH   := $(abspath $(lastword $(MAKEFILE_LIST)))
MAKEFILE_DIR    := $(notdir $(patsubst %/,%,$(dir $(MAKEFILE_PATH))))

# From: http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL   :=all
.PHONY          : all info dist release tests update-python-version check clean help

# =============================================================================
# MAIN RULES
# =============================================================================

all: $(PRODUCTS) $(BUILD_ALL) ## Builds all the products
	

info: ## Displays information about the project
	@echo libparsing: $(VERSION)

dist: $(PRODUCT) $(DIST_FILES) ## Creates source and binary Python distributions
	$(PYTHON) setup.py check clean sdist bdist

release: $(PRODUCT) update-python-version $(SOURCES)/python/lib$(PROJECT)/_lib$(PROJECT).so
	@echo "$(CYAN)📦  dist: $(RESET)"
	$(PYTHON) setup.py check clean
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	$(PYTHON) setup.py sdist bdist register upload

tests: $(TEST_PRODUCTS)

ffi: $(SOURCES)/alt$(PROJECT)/$(PROJECT).ffi ## Re-generates the FFI interface

update-python-version: $(SOURCES)/h/parsing.h
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' $(SOURCES)/python/$(PYMODULE)/__init__.py 
	sed -i 's/VERSION \+= *"[^"]\+"/VERSION            = "$(VERSION)"/' setup.py

check: $(SOURCES_C) $(SOURCES_H) ## Runs checks on the source code
	@# SEE: http://sourceforge.net/p/cppcheck/wiki/ListOfChecks/
	@echo "$(CYAN)📦  Checking: $(SOURCES_C) $(RESET)"
	@echo "$(RED)"
	@cppcheck --suppress=unusedFunction -Isrc/h --enable=all $(SOURCES_C)
	@echo "$(RESET)"
	@echo "$(CYAN)📦  Checking: $(SOURCES_PY) $(RESET)"
	@echo "$(RED)"
	@pychecker $(SOURCES_PY)
	@echo "$(RESET)"

clean: ## Cleans the build files
	@find . -name __pycache__ -exec rm -rf '{}' ';' ; true
	@echo $(PRODUCTS) $(BUILD_ALL) | xargs -n1 rm 2> /dev/null ; true
	@test -d $(DIST) && rm -rf $(DIST) ; true

help: ## Displays a description of the different Makefile rules
	@echo "$(CYAN)★★★ $(PROJECT) makefile ★★★$(RESET)"
	@grep -E -o '((\w|-)+):[^#]+(##.*)$$'  $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":|##"}; {printf "make \033[01;32m%-15s\033[0m🕮 %s\n", $$1, $$3}'

# =============================================================================
# PRODUCTS
# =============================================================================

$(DIST)/lib$(PROJECT).so: $(BUILD_SOURCES_O)
	@echo "$(GREEN)📝  $@ [SO]$(RESET)"
	@mkdir -p `dirname $@`
	@echo "$(CYAN)→ " $(BUILD_SOURCES_O) "$(RESET)"
	$(LD) -shared $(LDFLAGS) $(BUILD_SOURCES_O) -o $@

$(DIST)/lib$(PROJECT).so.$(VERSION): $(DIST)/lib$(PROJECT).so
	@echo "$(GREEN)📝  $@ [SO $(VERSION)]$(RESET)"
	@cp $< $@

$(DIST)/c-%: $(BUILD)/c-%.o $(SOURCES_O) $(DIST)/lib$(PROJECT).so
	@echo "$(GREEN)📝  $@ [EXE]$(RESET)"
	@mkdir -p `dirname $@`
	$(CC) -L$(DIST) -l$(PROJECT) $(LDFLAGS) $(OUTPUT_OPTION) $? 
	chmod +x $@

# =============================================================================
# PYTHON MODULE
# =============================================================================

$(SOURCES)/python/lib$(PROJECT)/lib$(PROJECT).so: $(DIST)/lib$(PROJECT).so
	@echo "$(GREEN)📝  $@ [PYTHON SO]$(RESET)"
	@cp $< $@

$(SOURCES)/python/lib$(PROJECT)/_libparsing.ffi: $(SOURCES)/h/$(PROJECT).h
	@echo "$(GREEN)📝  $@ [FFI]$(RESET)"
	@mkdir -p `dirname $@`
	./bin/ffigen.py $< > $@

$(SOURCES)/python/lib$(PROJECT)/_libparsing.c: $(SOURCES_C) $(SOURCES_H)
	$(CC) $(CFLAGS) -E -DWITH_CFFI $(SOURCES_C) | egrep -v '^#' > $@

$(SOURCES)/python/lib$(PROJECT)/_libparsing.so: $(BUILD_PY_FFI)
	$(PYTHON) $(SOURCES)/python/lib$(PROJECT)/_buildext.py $@

# =============================================================================
# OBJECTS
# =============================================================================

$(BUILD)/c-%.o: $(TESTS)/c-%.c $(SOURCES_H) $(DIST)/lib$(PROJECT).so Makefile
	@echo "$(GREEN)📝  $@ [C TEST]$(RESET)"
	@mkdir -p `dirname $@`
	$(COMPILE.c) -shared -Og -g $(OUTPUT_OPTION) $<

$(BUILD)/%.o: $(SOURCES)/c/%.c $(DEPDIR)/%.d Makefile
	@echo "$(GREEN)📝  $@ [C SOURCE]$(RESET)"
	@mkdir -p `dirname $@`
	$(COMPILE.c) $(OUTPUT_OPTION) $<

$(DEPDIR)/%.d: ;
.PRECIOUS: $(DEPDIR)/%.d

# === HELPERS =================================================================

print-%:
	@echo $*=
	@echo $($*) | xargs -n1 echo | sort -dr

clean-%:
	@echo $($*) | xargs -n1 echo | sort -dr | xargs -n1 rm

-include $(patsubst %,$(DEPDIR)/%.d,$(basename $(SRCS)))

# EOF
