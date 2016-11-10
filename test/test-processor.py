import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from libparsing import *

__doc__ = """
Tests the Python wrapper for the processing of matches. It should be
much faster than the pure-python processor.
"""

def grammar():
	g = Grammar(isVerbose=False)
	s = g.symbols
	g.token("NUMBER",     "\d+(\.\d+)?")
	g.token("NAME",       "\w+")
	g.token("WHITESPACE", "\s+")
	g.token("SPACE", "\s*")
	g.word("LP",        "(")
	g.word("RP",        ")")
	g.group("Atom",     s.NUMBER, s.NAME)
	g.group("Value")
	g.rule ("List",    s.LP, s.Value.zeroOrMore(), s.RP)
	s.Value.set(s.List, s.Atom)
	g.axiom = s.Value
	g.skip  = s.WHITESPACE
	return g

def process( value, r ):
	print (value, r)
	return value

def run():
	g = grammar() ; s = g.symbols
	p = g.parseString("(hello (w o r l d))")
	m = {} ; ids = 0
	print ("P", p)
	for k in dir(s):
		v = getattr(s,k)
		if isinstance(v, ParsingElement) and v.id >= 0:
			ids = max(ids, v.id)
			m[v.id] = process
	callbacks = [process] * ids
	#LIB.symbols.Processor_dispatchPython(p.match._cobject, callbacks)

if __name__ == "__main__":
	run()

# EOF
