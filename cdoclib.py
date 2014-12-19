#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : cdoclib
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 18-Dec-2014
# Last modification : 18-Dec-2014
# -----------------------------------------------------------------------------
import sys, re, fnmatch
import reporter, texto, templating
from pygments            import highlight
from pygments.lexers     import CLexer
from pygments.formatters import HtmlFormatter

VERSION = "0.0.0"
LICENSE = "http://ffctn.com/doc/licenses/bsd"

# START:DOC
__doc__ = """
== cdoclib
-- A C documentation and FFI generation utility

`cdoclib` extracts structure from specifically formatted C header files,
allowing to generate API documentation & Python CFFI data files.

The format is relatively simple: documentation and API is extracted from
comment strings put in the given header files. The documentation is expected to
be formatted in the `texto` (markdown-like) markup language.

You can see an example here <http://github.com/sebastien/parsing/src/parsing.h>
and the generated documentation <http://github.com/sebastien/parsing/parsing.html>.

Usage
=====

```
cdoclib include/header1.h include/header2.h
cdoclib include/header1.h include/header2.h
cdoclib include/header1.h include/header2.h  documentation.texto
cdoclib include/header1.h include/header2.h  documentation.html
cdoclib include/header1.h include/header2.h  documentation.ffi
```

Outputs
=======

`.texto`::
	outputs `texto`-formatted text with the annotated bits of code embedded

`.html`::
	outputs an HTML-formatted document designed ass an API reference

`.ffi`::
	outputs a subset of the header that should be parseable by Python's CFFI


Annotation `.h` files
=====================

The way to annotate structural elements within the header file is to use
one-line comments of the following form:

>	// @<CLASSIFIER>

where `<CLASSIFIER>` is one of the following:

- `@define`
- `@macro`
- `@callback`
- `@singleton`
- `@shared`
- `@type`
- `@operation`
- `@constructor`
- `@destructor`
- `@method`

Here's an example:

>	// @type ParsingContext
>	typedef struct ParsingContext {
>		struct Grammar*       grammar;      // The grammar used to parse
>		struct Iterator*      iterator;     // Iterator on the input data
>		struct ParsingOffset* offsets;      // The parsing offsets, starting at 0
>		struct ParsingOffset* current;      // The current parsing offset
>	} ParsingContext;

"""
# END:DOC

RE_DOC_LINE    = re.compile("\s*//(.*)")
RE_DOC_START   = re.compile("/\*\*?(.*)")
RE_DOC_BODY    = re.compile("\s*\*+\s*(.*)")
RE_DOC_END     = re.compile("\s*\*+/()")
RE_STRUCTURE   = re.compile("\s*@(\w+)\s*")
RE_EMPTY       = re.compile("^\s*$")
RE_ANNOTATION  = re.compile("^\s*(TODO|FIXME|SEE|NOTE).+")

RE_MACRO       = re.compile("#define\s+(\w+)")
RE_RETURN      = re.compile("\s*(\w+)")
RE_FUNCTION    = re.compile("\s*(extern|inline)?[\w_]+\s*[\*]*\s+([\w\_]+)")
RE_STRUCT      = re.compile("\s*typedef\s+struct\s+([\w_]+)")
RE_CALLBACK    = re.compile("\s*typedef\s+\w[\w\d_]*\s*\*?\s+\(\s*\*([\w\_]+)\s*\)")
RE_TYPEDEF     = re.compile("\s*typedef\s+\w[\w\d_]*\s*\*?\s+\s*([\w\_]+)\s*")
RE_SINGLE      = re.compile("\s*static\s+\w+\s+([\w_]+)")

TYPE_SYMBOL    = "S"
TYPE_DOC       = "D"
TYPE_CODE      = "C"
TYPE_FILE      = "F"

SYMBOL_EXTRACTORS = dict(
	define      = RE_MACRO,
	macro       = RE_MACRO,
	singleton   = RE_SINGLE,
	callback    = RE_CALLBACK,
	shared      = RE_FUNCTION,
	type        = RE_STRUCT,
	typedef     = RE_TYPEDEF,
	operation   = RE_FUNCTION,
	constructor = RE_RETURN,
	destructor  = RE_RETURN,
	method      = RE_FUNCTION,
)

HTML_PAGE = """
<!DOCTYPE html>
<html>
	<head>
		<meta charset="utf-8" />
		<title>${library} &mdash; API</title>
		<link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.4/styles/default.min.css">
		<link rel="stylesheet" href="http://sebastienpierre.ca/lib/css/base.css">
		<script src="http://cdnjs.cloudflare.com/ajax/libs/highlight.js/8.4/highlight.min.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/jquery-2.0.3.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/extend-2.5.0.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/html-5.0.3.js"></script>
		<script src="http://sebastienpierre.ca/lib/js/texto.js"></script>
		<style>${css}</style>
	<body>
		<div class="API use-texto use-base">
			<div class="hidden index to-w expand-h" style="position:fixed;overflow:auto;width:250px;">
				<ol>
				${for:groups}
				<li class="${this.classifier}"><a href="#${this.name}_${this.classifier}">${this.name}</a></li>
				${end}
				</ol>
			</div>
			<div class="documentation" style="margin-left:250px;">
				<div class="document">
				${body}
				</div>
			</div>
		</div>
	</body>
</html>
"""

def strip(lines):
	while lines and RE_EMPTY.match(lines[0]):  lines = lines[1:]
	while lines and RE_EMPTY.match(lines[-1]): lines = lines[:-1]
	return lines

class Library:

	def __init__( self, path=None ):
		self.symbols = {}
		self.files   = []
		self.groups  = []
		self.parse(path)

	def parse( self, *paths ):
		for path in paths:
			if not path: continue
			with file(path, "r") as f:
				self.addGroups(Parser.Groups(Parser.Lines(f.read())))
		return self

	def addGroups( self, groups ):
		self.groups += groups
		for g in groups:
			if g.type == TYPE_SYMBOL:
				self.symbols.setdefault(g.name, {})[g.classifier] = g
		return self

	def getSymbols( self, pattern, classifiers=None ):
		if classifiers and type(classifiers) not in (list, tuple): classifiers = list(classifiers)
		assert type(pattern) in (unicode, str)
		symbols = [_ for _ in self.groups if _.type == TYPE_SYMBOL and fnmatch.fnmatch(_.name, pattern)]
		if classifiers: symbols = [_ for _ in symbols if _.classifier in classifiers]
		return symbols

	def getSymbolsCode( self, pattern, classifiers=None ):
		return "\n".join(("\n".join(_.code) for _ in self.getSymbols(pattern, classifiers)))

	def getCode( self, *args ):
		res = []
		for p,c in args:
			res.append(self.getSymbolsCode(p,c))
		return "\n".join(res)


class Group:

	def __init__( self, type=None, name=None, code=None, doc=None, classifier=None, start=0 ):
		self.type = type
		self.name = name
		self.code = code
		self.start = start
		self.doc  = [] if doc  is None else doc
		self.code = [] if code is None else code
		self.classifier = classifier
		self.symbols    = {}

	def getCode( self, name ):
		return "\n".join(self.symbols[name].code)

class Parser:

	@classmethod
	def Lines( cls, text ):
		"""Iterates through the given text's lines, yielding
		`(number, type, line)` triples."""
		counter = 0
		for line in text.split("\n"):
			m = [m.group(1) for m in (_.match(line) for _ in (RE_DOC_LINE, RE_DOC_START, RE_DOC_BODY, RE_DOC_END)) if m]
			if m:
				s = RE_STRUCTURE.match(m[0])
				if s:
					t,l = TYPE_SYMBOL, s.group(1)
				else:
					t,l = TYPE_DOC, m[0]
					if RE_ANNOTATION.match(l) or l == "/":
						t,l = None, None
			else:
				t,l = TYPE_CODE, line
			counter += 1
			if t != None and l != None:
				yield counter, t, l

	@classmethod
	def Groups( cls, lines ):
		"""Creates groups out of the lines generated by `ParseLines`"""
		mode    = None
		current = root = Group(type=TYPE_FILE)
		result = [current]
		for i,t,l in lines:
			if   t == TYPE_SYMBOL:
				current = Group(
					type       = TYPE_SYMBOL,
					classifier = l.strip(),
					start      = i,
				)
				result.append(current)
			elif t == TYPE_DOC:
				if not current.code:
					current.doc.append(l)
				else:
					current  = Group(
						type = TYPE_FILE,
						doc  = [l],
						start = i,
					)
					result.append(current)
			elif t == TYPE_CODE:
				current.code.append(l)
		# Now we post_process groups
		for group in result:
			if group.type == TYPE_SYMBOL:
				try:
					first_line  = (_ for _ in group.code if _).next()
				except StopIteration:
					reporter.error("Cannot find code for type")
				match       = SYMBOL_EXTRACTORS[group.classifier].match(first_line)
				assert match, "Symbol extractor {0} cannot match {1}".format(group.classifier, first_line)
				group.name = match.groups()[-1]
				root.symbols[group.name] = group
		return result

class Formatter:

	def __init__( self ):
		self._codeLexer     = CLexer()
		self._codeFormatter = HtmlFormatter()

	def format( self, library ):
		index = []
		body  = []
		# The .h file usually starts with a preamble that we'd like to skip
		has_doc = 0
		for group in library.groups:
			d = []
			if group.name:
				l  = '\n[#%s_%s]`%s`' % (group.name, group.classifier, group.name)
				d.append(l)
				d.append("-" * len(l))
				d.append("")
			if group.doc:
				if has_doc > 0: d.append(u"\n".join(group.doc))
				has_doc += 1
			if group.code and has_doc > 1:
				code = strip([] + group.code)
				if code:
					code = "\n".join(code)
					# code = highlight(code, self._codeLexer, self._codeFormatter)
					code = "```c\n" + code + "\n```"
					d.append("\n" + code + "\n")
			body.append("\n".join(d))
		# We skip leading whitespace
		body = strip(body)
		return "\n".join(body)

def parse( *paths ):
	lib = Library()
	for _ in paths:
		lib.parse(_)
	return lib

if __name__ == "__main__":
	import ipdb
	args = sys.argv[1:] or ["src/parsing.h"]
	# reporter.install(reporter.StderrReporter)
	lib  = Library()
	for p in args:
		with open(p) as f:
			text   = f.read()
			for line in Parser.Lines(text):
				print line
			groups = Parser.Groups(Parser.Lines(text))
			lib.addGroups(groups)
	body = Formatter().format(lib)
	# if False:
	# 	print templating.Template(HTML_PAGE).apply(dict(
	# 		css  = open("texto.css").read(),
	# 		body = texto.toHTML(body),
	# 		groups = [_ for _ in lib.groups if _.type == TYPE_SYMBOL]
	# 	))
	# else:
	# 	print body
	# print lib.getSymbolCode("Iterator", "type")
	# with file("src/parsing.ffi", "w") as f:
	# 	f.write(lib.getSymbolCode("Reference",      "type"))
	# 	f.write(lib.getSymbolCode("Match",          "type"))
	# 	f.write(lib.getSymbolCode("ParsingElement", "type"))
	# 	f.write(lib.getSymbolCode("Grammar",        "type"))
	# 	# f.write(lib.getCode("Token",          "constructor"))
	# 	# f.write(lib.getCode("Word",           "constructor"))
	# 	# f.write(lib.getCode("Grammar",        "constructor"))

# EOF - vim: ts=4 sw=4 noet
