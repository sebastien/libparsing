from libparsing import *
import unittest

# -----------------------------------------------------------------------------
#
# TEST
#
# -----------------------------------------------------------------------------

class TestCollection: #(unittest.TestCase):

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
		libparsing = C_API.symbols
		r = libparsing.Reference_new()
		assert not libparsing.Reference_hasElement(r)
		assert not libparsing.Reference_hasNext(r)
		assert r.contents._b_needsfree_ is 0
		# SEE: https://docs.python.org/2.5/lib/ctypes-data-types.html
		assert r.contents.name == "_"
		self.assertEquals(r.contents.id, -10)
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
		text        = "pouet"
		w           = Word(text)
		g.axiom     = w
		g.isVerbose = False
		r           = g.parseString(text)
		assert r
		m           = r.match
		assert m
		self.assertEqual(m.status, "M")
		self.assertEqual(m.offset,  m.getOffset())
		self.assertEqual(m.length,  m.getLength())
		self.assertEqual(m.offset,  0)
		self.assertEqual(m.length,   len(text))
		self.assertIsNone(m.next)
		self.assertIsNone(m.child)

	def testRuleFlat( self ):
		libparsing = C_API.symbols
		g  = libparsing.Grammar_new()
		a  = libparsing.Word_new("a")
		b  = libparsing.Word_new("b")
		ab = libparsing.Rule_new(None)
		ra = libparsing.Reference_Ensure(a)
		rb = libparsing.Reference_Ensure(b)
		libparsing.ParsingElement_add(ab, ra)
		libparsing.ParsingElement_add(ab, rb)
		g.contents.axiom     = ab
		g.contents.isVerbose = 0
		libparsing.Grammar_parseString(g, "abab")

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
		self.assertEquals(g._wrapped.contents._b_needsfree_, 0)
		self.assertTrue(g._mustFree)
		self.assertEquals(a._wrapped.contents._b_needsfree_, 0)
		self.assertTrue(a._mustFree)
		self.assertEquals(a._wrapped.contents._b_needsfree_, 0)
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
		assert r.match.offset  == 0
		assert r.match.length  == 2
		assert r.match.range() == (0, 2)
		assert len(r.match.children()) == 2
		self.assertEquals([_.group() for _ in r.match], ["a", "b"])
		# We test child 1
		ma = r.match[0]
		# NOTE: The following assertions will fail for now
		# print ma.element()
		# assert isinstance(ma.element(), Word)
		self.assertEquals(ma.group(), "a")
		self.assertEquals(ma.range(), (0,1))
		mb = r.match[1]
		self.assertEquals(mb.group(), "b")
		self.assertEquals(mb.range(), (1,2))
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

		self.assertEquals(left.group(),  "1")
		self.assertEquals(op.group(),    "+")
		self.assertEquals(right.group(), "10")

		# We decompose the operator
		self.assertEquals(op[0].group(), "+")
		self.assertEquals(op.group(),    "+")
		self.assertEquals(op.groups(),  ["+"])

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

		self.assertEquals(s.Operation.id, 0)
		self.assertEquals(s.Value.id,     2)
		self.assertEquals(s.NUMBER.id,    4)
		self.assertEquals(s.VARIABLE.id,  6)
		self.assertEquals(s.OPERATOR.id,  8)

		# # We parse, and make sure it completes
		r = g.parseString("1+10")
		self.assertTrue(r.isSuccess())
		self.assertTrue(r.isComplete())

		p = Processor(g)
		p.on(s.NUMBER,    lambda _: ("N", int(_.value)))
		p.on(s.VARIABLE,  lambda _: ("V", _))
		p.on(s.Operation, lambda _, left, op, right: (op, left, right))

		res = p.process(r)
		self.assertEquals(res, ("+", ("N", 1), ("N", 10)))

# -----------------------------------------------------------------------------
#
# TEST ELEMENTS
#
# -----------------------------------------------------------------------------

class TestElements(unittest.TestCase):


	# def testReferenceOptional( self ):
	# 	g = Grammar(isVerbose=True)
	# 	s = g.symbols
	# 	g.word("A", "a")
	# 	g.word("B", "b")
	# 	# We create a na optional rule
	# 	g.rule("Statement", s.A, s.B.optional())
	# 	# Make sure that the cardinality is set
	# 	self.assertEquals(s.Statement[1].cardinality, CARDINALITY_OPTIONAL)
	# 	g.axiom = s.Statement
	# 	# a -- must be complete
	# 	# r = g.parseString("a")
	# 	# self.assertTrue(r.isSuccess())
	# 	# self.assertTrue(r.isComplete())
	# 	# # ab -- must be complete
	# 	# r = g.parseString("ab")
	# 	# self.assertTrue(r.isSuccess())
	# 	# self.assertTrue(r.isComplete())
	# 	# abb -- must be partial
	# 	r = g.parseString("abb")
	# 	self.assertEquals(r.offset, 2)
	# 	self.assertTrue(r.isSuccess())
	# 	self.assertFalse(r.isComplete())

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

		print "XXX", v

		# We have reference matches first
		assert isinstance(left,     ReferenceMatch)
		assert isinstance(op,       ReferenceMatch)
		assert isinstance(right,    ReferenceMatch)

		# Which themselves hold group matches
		assert isinstance(left[0],  GroupMatch)
		assert isinstance(op[0],    TokenMatch)
		assert isinstance(right[0], GroupMatch)

		self.assertEquals(left.group(),  "1")
		self.assertEquals(op.group(),    "+")
		self.assertEquals(right.group(), "10")

		# We decompose the operator
		self.assertEquals(op[0].group(), "+")
		self.assertEquals(op.group(),    "+")
		self.assertEquals(op.groups(),  ["+"])

if __name__ == "__main__":
	unittest.main()

# EOF - vim: ts=4 sw=4 noet
