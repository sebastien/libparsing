#!/bin/bash
# Get project root (script is in examples/, project root is parent)
cd "$(dirname "$(dirname "$0")")"

if [ ! -f parsing-lisp ]; then
    echo "Compiling parser..."
    gcc -I src/h examples/parsing-lisp.example.c -L dist -lparsing -o parsing-lisp
fi

if [ $# -eq 0 ]; then
    echo "Parsing example file: examples/parsing-lisp.example.lsp"
    LD_LIBRARY_PATH=dist ./parsing-lisp examples/parsing-lisp.example.lsp
else
    echo "Parsing file: $1"
    LD_LIBRARY_PATH=dist ./parsing-lisp "$1"
fi