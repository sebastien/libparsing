#!/usr/bin/env python2.7
import os, sys ; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/python")
from libparsing import *
import unittest

# -----------------------------------------------------------------------------
#
# TEST
#
# -----------------------------------------------------------------------------

class TestCollection(unittest.TestCase):

	def testCTypesBehaviour( self ):
		"""A few assertions about what to expect from CTypes."""
		# We retrieve the TReference type
		ref = C.TYPES["Reference*"]
		assert ref.__name__.endswith("LP_TReference")
		# We create a new reference pointer, which is a NULL pointer
		r = ref()
		# NULL pointers have a False boolean value
		assert not r
		assert not bool(r)
		assert r is not False
		assert r is not None
		# And raise a ValueError when accessed
		was_null = False
		try:
			r.contents
		except ValueError as e:
			assert "NULL pointer access" in str(e)
			was_null = True
		assert was_null

	def testReference( self ):
		# We're trying to assert that Reference objects created from C
		# work as expected.
		libparsing = LIB.symbols
		r = libparsing.Reference_new()
		assert not libparsing.Reference_hasElement(r)
		assert not libparsing.Reference_hasNext(r)
		assert r.contents._b_needsfree_ is 0
		# SEE: https://docs.python.org/2.5/lib/ctypes-data-types.html
		self.assertEqual(r.contents.name, b"_")
		self.assertEqual(r.contents.id, -10)
		# So that's the surprising stuff about ctypes. Our C code assigns
		# NULL to element and next. If we had declared TReference with
		# `next` and `element` as returning `void*`, then we would
		# get None. But because they're ParsingElement* and Reference*
		# they return these pointers pointing to NULL.
		assert not r.contents.element
		assert not r.contents.next
		assert r.contents.element is not None
		assert r.contents.next    is not None
		r.contents.element = None
		r.contents.next    = None
		assert isinstance(r.contents.element, C.TYPES["ParsingElement*"])
		assert isinstance(r.contents.next,    C.TYPES["Reference*"])
		# And the C addresses of the element and next (which are NULL pointers)
		# is not 0. This is because `addressof` returns the object of the Python
		# pointer instance, not the address of its contents.
		assert ctypes.addressof(r.contents.element) != 0
		assert ctypes.addressof(r.contents.next)    != 0
		# Anyhow, we now creat an empty rule
		ab = libparsing.Rule_new(None)
		assert ab.contents._b_needsfree_ is 0

	def testSimpleGrammar( self ):
		g           = Grammar()
		text        = b"pouet"
		w           = Word(text)
		g.axiom     = w
		g.isVerbose = False
		r           = g.parseString(text)
		assert r
		m           = r.match
		assert m
		self.assertEqual(m.status, b"M")
		self.assertEqual(m.offset or 0,  m.getOffset())
		self.assertEqual(m.length or 0,  m.getLength())
		self.assertEqual(m.offset or 0,  0)
		self.assertEqual(m.length or 0,  len(text))
		self.assertIsNone(m.next)
		self.assertFalse(m.children and True or False)

	def testRuleFlat( self ):
		libparsing = LIB.symbols
		g  = libparsing.Grammar_new()
		a  = libparsing.Word_new(b"a")
		b  = libparsing.Word_new(b"b")
		ab = libparsing.Rule_new(None)
		ra = libparsing.Reference_FromElement(a)
		rb = libparsing.Reference_FromElement(b)
		libparsing.ParsingElement_add(ab, ra)
		libparsing.ParsingElement_add(ab, rb)
		g.contents.axiom     = ab
		g.contents.isVerbose = 0
		libparsing.Grammar_parseString(g, b"abab")

	def testRuleOO( self ):
		g       = Grammar()
		text    = "abab"
		a       = Word("a")
		b       = Word("b")
		ab      = Rule()
		ra      = Reference.Ensure(a)
		rb      = Reference.Ensure(b)
		ab.add(ra)
		ab.add(rb)
		g.axiom = ab
		g.isVerbose = True
		r = g.parseString(text)

	def testMemory( self ):
		# In this case Word and Grammar should all be freed upon deletion.
		a = Word("a")
		b = Word("b")
		g = Grammar(
			isVerbose = True,
			axiom     = Rule(a, b)
		)
		self.assertEqual(g._cobject._b_needsfree_, 0)
		self.assertTrue(g._mustFree)
		self.assertEqual(a._cobject._b_needsfree_, 0)
		self.assertTrue(a._mustFree)
		self.assertEqual(a._cobject._b_needsfree_, 0)
		self.assertTrue(a._mustFree)

	def testMatch(self):
		# We use the fancier shorthands
		g = Grammar(
			isVerbose = False,
			axiom     = Rule(Word("a"), Word("b"))
		)
		r = g.parseString("abab")
		# We test the parsing result
		assert isinstance(r, ParsingResult)
		assert not r.isFailure()
		assert r.isSuccess()
		assert r.isPartial()
		assert not r.isComplete()
		# We ensure that the over offset matches
		assert isinstance(r.match, RuleMatch)
		self.assertEqual(r.match.offset or 0, 0)
		self.assertEqual(r.match.length or 0, 2)
		self.assertEqual(r.match.range() , (0, 2))
		assert len(r.match.children) == 2
		self.assertEqual([_.group() for _ in r.match], [[b"a"], [b"b"]])
		self.assertEqual([_.value   for _ in r.match], [b"a", b"b"])
		# We test child 1
		ma = r.match[0]
		# NOTE: The following assertions will fail for now
		# print ma.element()
		# assert isinstance(ma.element(), Word)
		self.assertEqual(ma.group(), [b"a"])
		self.assertEqual(ma.value,    b"a")
		self.assertEqual(ma.range(), (0,1))
		mb = r.match[1]
		self.assertEqual(mb.group(), [b"b"])
		self.assertEqual(mb.value,   b"b")
		print ("XXX MB", mb.value, mb.length, mb.offset)
		self.assertEqual(mb.range(), (1,2))
		# NOTE: The following creates core dump... ahem
		#for i,m in enumerate(r.match.children()):
		#	print "Match", i, "=", m, m.name(), m.element(), m.cardinality(), list(m.children()), m.group(), m.range()

	def testReferenceMatch(self):
		"""Reference matches are probably the hardest thing to understand
		in therms of API. They wrap parsing element matches."""
		NUMBER     = Token("\d+")
		VARIABLE   = Token("\w+")
		OPERATOR   = Token("[\+\-*\/]")
		Value      = Group(NUMBER, VARIABLE)
		Operation  = Rule(
			Value._as("left"), OPERATOR._as("op"), Value._as("right")
		)
		g = Grammar(
			isVerbose = False,
			axiom     = Operation
		)
		# We parse, and make sure it completes
		r = g.parseString("1+10")
		self.assertTrue(r.isSuccess())
		self.assertTrue(r.isComplete())

		# The individual retrieval of object is slower than the one shot
		left  = r.match.get("left")
		op    = r.match.get("op")
		right = r.match.get("right")

		# We also assert the querying as a whole dictionary
		v     = r.match.get()
		assert "left"  in v
		assert "op"    in v
		assert "right" in v

		# We have reference matches first
		assert isinstance(left,     ReferenceMatch)
		assert isinstance(op,       ReferenceMatch)
		assert isinstance(right,    ReferenceMatch)

		# Which themselves hold group matches
		assert isinstance(left[0],  GroupMatch)
		assert isinstance(op[0],    TokenMatch)
		assert isinstance(right[0], GroupMatch)

		self.assertEqual(left.value,  b"1")
		self.assertEqual(op.value,    b"+")
		self.assertEqual(right.value, b"10")

		# We decompose the operator
		self.assertEqual(op[0].group(), b"+")
		self.assertEqual(op.group(),   [b"+"])

	def testGrammarSymbols(self):
		g = Grammar(isVerbose = False)
		s = g.symbols
		g.token("NUMBER",   "\d+")
		g.token("VARIABLE", "\w+")
		g.token("OPERATOR", "[\+\-*\/]")
		g.group("Value",    s.NUMBER, s.VARIABLE)
		g.rule ("Operation",
			s.Value._as("left"), s.OPERATOR._as("op"), s.Value._as("right")
		)
		g.axiom = s.Operation

		# # We parse, and make sure it completes
		r = g.parseString("1+10")
		self.assertTrue(r.isSuccess())
		self.assertTrue(r.isComplete())

	def testProcessor(self):
		g = Grammar(isVerbose = False)
		s = g.symbols
		g.token("NUMBER",   "\d+")
		g.token("VARIABLE", "\w+")
		g.token("OPERATOR", "[\+\-*\/]")
		g.group("Value",    s.NUMBER, s.VARIABLE)
		g.rule ("Operation",
			s.Value._as("left"), s.OPERATOR._as("op"), s.Value._as("right")
		)
		g.axiom = s.Operation

		# Calling prepare will process the symbols
		g.prepare()

		self.assertEqual(s.Operation.id, 0)
		self.assertEqual(s.Value.id,     2)
		self.assertEqual(s.NUMBER.id,    4)
		self.assertEqual(s.VARIABLE.id,  6)
		self.assertEqual(s.OPERATOR.id,  8)

		# # We parse, and make sure it completes
		r = g.parseString("1+10")
		self.assertTrue(r.isSuccess())
		self.assertTrue(r.isComplete())

		p = Processor(g)
		p.on(s.NUMBER,    lambda _: ("N", int(_.value)))
		p.on(s.VARIABLE,  lambda _: ("V", _))
		p.on(s.Operation, lambda _, left, op, right: (op, left, right))

		res = p.process(r.match)
		self.assertEqual(res, (b"+", ("N", 1), ("N", 10)))

	def testParsingContext( self ):
		c = ParsingContext(None, None)
		# Default state
		self.assertEqual(c.getVariableCount(), 1)
		self.assertEqual(c.get("depth"), None)
		self.assertEqual(c.get("hello"), None)
		# Setting a variable
		# We want to make sure that setting a variable twice does not
		# create more variables
		c.set("hello", 1)
		self.assertEqual(c.getVariableCount(), 2)
		self.assertEqual(c.get("hello"), 1)
		c.set("hello", 2)
		self.assertEqual(c.getVariableCount(), 2)
		self.assertEqual(c.get("hello"), 2)
		c.set("hello", 1)
		self.assertEqual(c.getVariableCount(), 2)
		self.assertEqual(c.get("hello"), 1)
		# Pushing the scope
		c.push()
		self.assertEqual(c.getVariableCount(), 3)
		self.assertEqual(c.get("depth"), 2)
		self.assertEqual(c.get("hello"), 1)
		# We're redefining a variable defined in a parent scope,
		# this means that we add a new variable
		c.set("hello", 2)
		self.assertEqual(c.get("hello"), 2)
		self.assertEqual(c.getVariableCount(), 4)
		# Popping the scope
		c.pop()
		self.assertEqual(c.getVariableCount(), 2)
		self.assertEqual(c.get("hello"), 1)
		self.assertEqual(c.get("depth"), None)
		# It's safe to pop again
		c.pop()
		self.assertEqual(c.getVariableCount(), 1)
		self.assertEqual(c.get("hello"), None)
		self.assertEqual(c.get("depth"), None)
		# and again
		c.pop()
		self.assertEqual(c.getVariableCount(), 1)
		self.assertEqual(c.get("hello"), None)
		self.assertEqual(c.get("depth"), None)


if __name__ == "__main__":
	unittest.main()

# EOF - vim: ts=4 sw=4 noet
