#!/usr/bin/env python
import sys
"""
Shows the 100 characters after the given index on the given files

cut-after <FILE>... <INDEX>
"""
i = int(sys.argv[-1])
for a in sys.argv[1:-1]:
	print "%-20s:%04d:%s" % (a, i, repr(open(a).read()[i:i+100])[1:-1])
# EOF
