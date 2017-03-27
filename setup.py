# encoding: utf-8
# SEE: https://packaging.python.org/en/latest/distributing.html#id23
# SEE: https://pythonhosted.org/setuptools/setuptools.html
# --
# Create source distribution: python setup.py sdist
# Upload using twine: twine upload dist/*
# Upload using setup.py: setup.py sdist bdist_wheel upload
try:
	from setuptools import setup, Extension
except ImportError:
	from distutils.core import setup, Extension
import sys, os, tempfile

# We make sure `build_libparsing` is within the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))

VERSION            = "0.9.2"
if os.path.exists("src/h/parsing.h"):
	LONG_DESCRIPTION = "\n".join(_[2:].strip() for _ in open("src/h/parsing.h").read().split("[START:INTRO]",1)[1].split("[END:INTRO]")[0].split("\n"))
else:
	LONG_DESCRIPTION = ""

# If pandoc is installed, we translate the documentation to RST. This is really
# only useful for publishing, not for building.
if LONG_DESCRIPTION and os.popen("which pandoc").read():
	p = tempfile.mktemp()
	with open(p,"w") as f: f.write(LONG_DESCRIPTION)
	LONG_DESCRIPTION = os.popen("pandoc -f markdown -t rst %s" % (p)).read()
	os.unlink(p)

setup(
	name             = "libparsing",
	version          = VERSION,
	url              = "https://github.com/sebastien/libparsing",
	# download_url     = "",
	author           = 'Sébastien Pierre',
	author_email     = 'sebastien.pierre@gmail.com',
	license          = 'BSD',
	description      = "Python wrapper for libparsing, a PEG-based parsing library written in C",
	keywords         = "parsing PEG grammar libparsing",
	long_description = LONG_DESCRIPTION,
	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers=[
		'Development Status :: 4 - Beta',
		'Intended Audience :: Developers',
		'Topic :: Software Development :: Build Tools',
		'License :: OSI Approved :: BSD License',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.4',
	],
	packages    = ["libparsing"],
	package_dir = {"libparsing":"src/python/libparsing"},
	package_data ={
		"libparsing":[
			"_libparsing.c",
			"_libparsing.h",
			"_libparsing.ffi",
			"_buildext.py",
		]
	},
	# SEE: http://cffi.readthedocs.io/en/latest/cdef.html?highlight=setup.py
	setup_requires=["cffi>=1.9.1"],
	cffi_modules=["src/python/libparsing/_buildext.py:FFI_BUILDER"],
	install_requires=["cffi>=1.9.1"],
)

# EOF
