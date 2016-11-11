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

def process( value=None, r=None ):
	return value

def run():
	g = grammar() ; s = g.symbols
	p = g.parseString("((h as asdasds sadaasd) (w o r l d))")
	m = {} ; ids = 0
	# for k in dir(s):
	# 	v = getattr(s,k)
	# 	if isinstance(v, ParsingElement) and v.id >= 0:
	# 		ids = max(ids, v.id)
	# 		m[v.id] = process
	# callbacks = [process] * ids
	callbacks = [lambda x,y:process(x)] * 100
	res = LIB.symbols.Match_processPython(p.match._cobject, callbacks)

if __name__ == "__main__":
	run()

# EOF
