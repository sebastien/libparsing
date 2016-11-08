#!/usr/bin/env python3
import re, sys

# try:
import reporter
reporter.template(reporter.TEMPLATE_COMPACT)
logging = reporter.bind("memcheck")
# except Exception as e:
# 	print("PROBLEM", e)
# 	import logging
#
__doc__ = """
`memcheck` is a tool that parses the output of memory-related operations
as defined in `oo.h` and ensures the following properties:

- Any freed pointer was previously allocated
- Any created/resized pointer is deallocated
- No pointer is deallocated more than once

To use memcheck, run your program compiled with `<oo.h>` using the
`__NEW`, `__FREE`, ‥ primitives, save the output to a log
file and run `memcheck` on it.

```bash
./a.out > a.log
./bin/memcheck.py a.log
```

"""

ADDR         = "(\(nil\)|0x[\w\d]+)"
SIZE         = "(\d+)"

OP           = re.compile("^memcheck:(.+)\t.*$")
NEW          = re.compile("__NEW\(" + ADDR + "\)")
FREE         = re.compile("__FREE\(" + ADDR + "\)")
RESIZE       = re.compile("__RESIZE\(" + ADDR + "," + SIZE + "\)")
ARRAY_NEW    = re.compile("__ARRAY_NEW\(" + ADDR + "," + SIZE + " * " + SIZE  + "\)=" + ADDR)
ARRAY_RESIZE = re.compile("__ARRAY_RESIZE\(" + ADDR + "," + SIZE + "\)=" + ADDR)
STRING_COPY  = re.compile("__STRING_COPY\(" + ADDR + "\)")

def match_op( line ):
	"""Parses a line from a log file containing `memcheck:‥` lines, extracting
	a couple `(operation, matches)` for each matching line."""
	OPS = (NEW, FREE, RESIZE, ARRAY_NEW, ARRAY_RESIZE, STRING_COPY)
	m = OP.match(line)
	if not m:
		return (None, None)
	line = m.group(1)
	for op in OPS:
		m = op.match(line)
		if m:
			return (op, m.groups())
	return (None, None)

def memcheck( path, strict=False ):
	"""Parses the given log file, trying to extract memory pointer information.
	"""
	logging.info("Checking {0}".format(path))
	pointers = {}
	with open(path, "r") as f:
		for l, line in enumerate(f.readlines()):
			op, match = match_op(line)
			if op is None:
				if strict or OP.match(line):
					logging.error("Could not parse line: {0}".format(repr(line)))
			elif op is NEW or op is STRING_COPY:
				addr, = match
				ptr = pointers.setdefault(addr, dict(current=addr, previous=addr, free=None, allocs=0, deallocs=0, resized=0, lines=[]))
				ptr["current"] = addr
				ptr["allocs"] += 1
				ptr["lines"].append((l,op,match))
			elif op is FREE:
				addr, = match
				if not ptr.get(addr):
					ptr = pointers.setdefault(addr, dict(current=None, previous=None, free=addr, allocs=0, deallocs=1, resized=0, lines=[]))
				ptr["free"]      = addr
				ptr["deallocs"] += 1
				ptr["lines"].append((l,op,match))
			# elif op is RESIZE:
			# 	addr, = match
			# 	if not ptr.get(addr):
			# 		ptr = pointers.setdefault(addr, dict(current=None, previous=None, free=addr, allocs=0, deallocs=1, resized=0, lines=[]))
	return pointers

def analyse( pointers ):
	"""Analyses the result from a memcheck and produces a report."""
	unfreed   = []
	overfreed = []
	freed     = []
	for addr in sorted(pointers.keys()):
		ptr = pointers[addr]
		if   ptr["allocs"] > ptr["deallocs"]:
			unfreed.append(addr)
		elif ptr["allocs"] < ptr["deallocs"]:
			overfreed.append(addr)
		elif ptr["allocs"] == ptr["deallocs"]:
			freed.append(addr)

	logging.info("{0} properly freed pointers:".format(len(freed)))
	for _ in freed:
		logging.info("\t{0}".format(_))
	if unfreed:
		logging.info("{0} unfreed pointers:".format(len(unfreed)))
		for _ in unfreed:
			logging.info("\t{0}".format(_))
	if overfreed:
		logging.info("{0} overfreed pointers:".format(len(overfreed)))
		for _ in overfreed:
			logging.info("\t{0}".format(_))

if __name__ == "__main__":
	for _ in sys.argv[1:]:
		analyse(memcheck(_))

# EOF
