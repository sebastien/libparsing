# encoding: utf-8
# SEE: https://packaging.python.org/en/latest/distributing.html#id23
# SEE: https://pythonhosted.org/setuptools/setuptools.html
# --
# Create source distribution: python setup.py sdist
# Upload using twine: twine upload dist/*
# Upload using setup.py: setup.py sdist bdist_wheel upload
from distutils.core import setup, Extension

grep = lambda f,e:(l for l in file(f).readlines() if l.startswith(e)).next()

# SEE: https://docs.python.org/2/distutils/apiref.html#distutils.core.Extension
libparsing = Extension("libparsing",
	define_macros       = [("PYTHON", "1")],
	include_dirs        = ["/usr/local/include", "src"],
	extra_compile_args =  ["-std=c11"],
	libraries           = ["pcre"],
	library_dirs        = ["/usr/local/lib"],
	sources             = ["src/parsing.c"]
)

setup(
	name             = "libparsing",
	version          = (l.split('"')[1] for l in file("src/parsing.h").readlines() if l.startswith("#define __PARSING_VERSION__")).next(),
	url              = "https://github.com/sebastien/libparsing",
	# download_url     = "",
	author           = 'Sébastien Pierre',
	license          = 'BSD',
	description      = "Python wrapper for libparsing, a PEG-based parsing library written in C",
	keywords         = 'parsing,grammar,libparsing,PEG',
	long_description = """\
	`libparsing` is a parsing element grammar (PEG) library written in C with
	Python bindings. It offers a fairly good performance while allowing for a
	lot of flexibility. It mainly intended to be used to create programming
	languages and software engineering tools.

	As opposed to more traditional parsing techniques, the grammar is not compiled
	but constructed using an API that allows dynamic update of the grammar.

	The parser does not do any tokeninzation, the instead input stream is
	consumed and parsing elements are dynamically asked to match the next
	element of it. Once parsing elements match, the resulting matched input is
	processed and an action is triggered.

	Parsing elements support:

	- backtracking, ie. going back in the input stream if a match is not found
	- cherry-picking, ie. skipping unrecognized input
	- contextual rules, ie. a rule that will match or not depending on external
	  variables
	 - dynamic grammar update, where you can change the grammar on the fly

	Parsing elements are usually slower than compiled or FSM-based parsers as
	they trade performance for flexibility. It's probably not a great idea to
	use them if parsing has to happen as fast as possible (ie. a protocol
	implementation), but it is a great use for programming languages, as it
	opens up the door to dynamic syntax plug-ins and multiple language
	embedding.

	If you're interested in PEG, you can start reading Brian Ford's original
	article. Projects such as PEG/LEG by Ian Piumarta <http://piumarta.com/software/peg/>
	,OMeta by Alessandro Warth <http://www.tinlizzie.org/ometa/>
	or Haskell's Parsec library <https://www.haskell.org/haskellwiki/Parsec>
	are of particular interest in the field.
	""",
	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers=[
		'Development Status :: 4 - Beta',
		'Intended Audience :: Developers',
		'Topic :: Software Development :: Build Tools',
		'License :: OSI Approved :: BSD License',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.6',
		'Programming Language :: Python :: 2.7',
		# 'Programming Language :: Python :: 3',
		# 'Programming Language :: Python :: 3.2',
		# 'Programming Language :: Python :: 3.3',
		# 'Programming Language :: Python :: 3.4',
	],
	package_dir = {"":"python"},
	packages    = ["libparsing"],
	package_data={
		"libparsing":["*.ffi"]
	},
	data_files = [
		("libparsing", ("src/parsing.c", "src/parsing.h", "src/oo.h"))
	],
	ext_modules = [libparsing],
)

# EOF
