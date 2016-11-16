from __future__ import print_function
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from libparsing import *
import unittest

__doc__ = """
Exercises how the processor predicably creates values, comparing both
processsing stategies (eager or lazy).

The grammar defined here defines a Lisp-ish language with either parens
or square-brackets enclosed expressions. The parens/brackets are prefixed
with the expected cardinality of their content.
"""

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
	g.rule ("List1_1",   s.LP1_1, s.Value,                           s.RP)
	g.rule ("List1_N",   s.LP1_N, s.Value.oneOrMore(),               s.RP)

	g.rule ("List0_1R",  s.LB0_1, s.Value.optional()._as("value"),   s.RB)
	g.rule ("List0_NR",  s.LB0_N, s.Value.zeroOrMore()._as("value"), s.RB)
	g.rule ("List1_1R",  s.LB1_1, s.Value._as("value"),              s.RB)
	g.rule ("List1_NR",  s.LB1_N, s.Value.oneOrMore()._as("value"),  s.RB)
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
		return ("W", self.process(match))

	def onTOKEN( self, match ):
		return ("T", self.process(match))

	def onAtom( self, match ):
		return self.process(match[0])

	def onValue( self, match ):
		return self.process(match[0])

	def onList( self, match ):
		return self.process(match[0])

	def onList0_1( self, match ):
		return ("L01", self.process(match[1]))

	def onList0_N( self, match ):
		return tuple(["L0N"] + self.process(match[1]))

	def onList1_1( self, match ):
		return ("L11", self.process(match[1]))

	def onList1_N( self, match ):
		return tuple(["L1N"] + self.process(match[1]))

	def onList0_1R( self, match ):
		return ("L01R", self.process(match[1]))

	def onList0_NR( self, match ):
		return tuple(["L0NR"] + self.process(match[1]))

	def onList1_1R( self, match ):
		return ("L11R", self.process(match[1]))

	def onList1_NR( self, match ):
		return tuple(["L1NR"] + self.process(match[1]))

def process( value=None, r=None ):
	return value

EXAMPLES = (
	"1..1(hello)",
	("L11", ("T", "hello")),
)

EXAMPLES = (
	"#t",
	("W", "#t"),

	"hello",
	("T", "hello"),

	"0..1()",
	("L01", None),

	"0..1(hello)",
	("L01", ("T", "hello")),

	"0..*()",
	("L0N",),

	"0..*(hello)",
	("L0N", ("T", "hello")),

	"0..*(hello world)",
	("L0N", ("T", "hello"), ("T", "world")),

	"1..1(hello)",
	("L11", ("T", "hello")),

	"1..*(hello)",
	("L1N", ("T", "hello")),

	"1..*(hello world)",
	("L1N", ("T", "hello"), ("T", "world")),

	"0..1[]",
	("L01R", None),

	"0..1[hello]",
	("L01R", ("T", "hello")),

	"0..*[]",
	("L0NR",),

	"0..*[hello]",
	("L0NR", ("T", "hello")),

	"0..*[hello world]",
	("L0NR", ("T", "hello"), ("T", "world")),

	"1..1[hello]",
	("L11R", ("T", "hello")),

	"1..*[hello]",
	("L1NR", ("T", "hello")),

	"1..*[hello world]",
	("L1NR", ("T", "hello"), ("T", "world")),

)

# -----------------------------------------------------------------------------
#
# TEST
#
# -----------------------------------------------------------------------------

class TestCollection(unittest.TestCase):

	def testBoth( self ):
		g = grammar() ; s = g.symbols
		n = len(EXAMPLES) / 2
		for i in range(n):
			source = EXAMPLES[i * 2]
			result = EXAMPLES[i * 2 + 1]
			r = g.parseString(source)
			self.assertTrue(r.isSuccess(), "Failed parsing: {0}".format(source))
			pe = P1(g).asEager()
			pl = P1(g).asLazy()
			re = pe.process(r)
			rl = pl.process(r)
			self.assertEqual(re, result)
			self.assertEqual(rl, result)

if __name__ == "__main__":
	unittest.main()

# EOF
