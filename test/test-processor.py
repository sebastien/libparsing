from __future__ import print_function
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from libparsing import *

__doc__ = """
Tests the PureProcessor and FastProcessors classes, making sure they
yield the same result.

The grammar defined here defines a Lisp-ish language with either parens
or square-brackets enclosed expressions. The parens/brackets are prefixed
with the expected cardinality of their content.
"""

EXAMPLES = (
"#t",
"hello",
"0..1()",
"0..1(hello)",
"0..*()",
"0..*(hello)",
"0..*(hello world)",
"1..1(hello)",
"1..*()",
"1..*(hello)",
"1..*(hello world)",
"0..1[]",
"0..1[hello]",
"0..*[]",
"0..*[hello]",
"0..*[hello world]",
"1..1[hello]",
"1..*[]",
"1..*[hello]",
"1..*[hello world]",
)
def grammar():
	"""Creates a grammar that has all the different types of parsing
	elements"""
	g = Grammar(isVerbose=False)
	s = g.symbols
	g.word( "WORD",       "#t")
	g.token("TOKEN",      "\w+")
	g.token("WHITESPACE", "\s+")
	g.word ("LP0_1",       "0..1(")
	g.word ("LP0_N",       "0..*(")
	g.word ("LP1_1",       "1..1(")
	g.word ("LP1_N",       "1..*(")
	g.word ("LB0_1",       "0..1[")
	g.word ("LB0_N",       "0..*[")
	g.word ("LB1_1",       "1..1[")
	g.word ("LB1_N",       "1..*[")
	g.word ("RP",          ")")
	g.word ("RB",          "]")
	g.group("Atom",     s.WORD, s.TOKEN)
	g.group("Value")
	g.rule ("List0_1",   s.LP0_1, s.Value.optional(),                s.RP)
	g.rule ("List0_N",   s.LP0_N, s.Value.zeroOrMore(),              s.RP)
	g.rule ("List1_1",   s.LP0_1, s.Value,                           s.RP)
	g.rule ("List1_N",   s.LP0_1, s.Value.oneOrMore(),               s.RP)
	g.rule ("List0_1R",  s.LB0_1, s.Value.optional()._as("value"),   s.RB)
	g.rule ("List0_NR",  s.LB0_N, s.Value.zeroOrMore()._as("value"), s.RB)
	g.rule ("List1_1R",  s.LB0_1, s.Value._as("value"),              s.RB)
	g.rule ("List1_NR",  s.LB0_1, s.Value.oneOrMore()._as("value"),  s.RB)
	g.group("List",
		s.List0_1 , s.List0_N , s.List1_1,  s.List1_N,
		s.List0_1R, s.List0_NR, s.List1_1R, s.List1_NR,
	)

	s.Value.set(s.List, s.Atom)
	g.axiom = s.Value
	g.skip  = s.WHITESPACE
	return g

class P1(Processor):

	def onWORD( self, match ):
		return match

	def onTOKEN( self, match ):
		return match

	def onAtom( self, match ):
		return match

	def onValue( self, match ):
		return match

	def onList( self, match ):
		return match

	def onList0_1( self, match ):
		return match

	def onList0_N( self, match ):
		return match

	def onList1_1( self, match ):
		return match

	def onList1_N( self, match ):
		return match

	def onList0_1R( self, match ):
		return match

	def onList0_NR( self, match ):
		return match

	def onList1_1R( self, match ):
		return match

	def onList1_NR( self, match ):
		return match

def process( value=None, r=None ):
	return value

def run():
	g = grammar() ; s = g.symbols
	for _ in EXAMPLES:
		print ("Parsing: {0}".format(_))
		r = g.parseString(_)
		if not r.isSuccess():
			print ("Parsing failed:", _)
			break
		p = P1(g)
		print ("RESULT=", p.process(r))


if __name__ == "__main__":
	run()

# EOF
