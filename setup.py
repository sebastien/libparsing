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


LONG_DESCRIPTION = "\n".join(_[2:].strip() for _ in open("src/h/parsing.h").read().split("[START:INTRO]",1)[1].split("[END:INTRO]")[0].split("\n"))
# If pandoc is installed, we translate the documentation to RST. This is really
# only useful for publishing, not for building.
if os.popen("which pandoc").read():
	p = tempfile.mktemp()
	with open(p,"w") as f: f.write(LONG_DESCRIPTION)
	LONG_DESCRIPTION = os.popen("pandoc -f markdown -t rst %s" % (p)).read()
	os.unlink(p)

setup(
	name             = "libparsing",
	version          = [l.split('"')[1] for l in open("src/h/parsing.h").readlines() if l.startswith("#define __PARSING_VERSION__")][0],
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
	package_dir = {"":"src/python"},
	packages    = ["libparsing"],
	data_files  = [
		("libparsing", (
			"src/python/libparsing/_libparsing.c",
			"src/python/libparsing/_libparsing.h",
			"src/python/libparsing/_libparsing.ffi"
		))
	],
	# SEE: http://cffi.readthedocs.io/en/latest/cdef.html?highlight=setup.py
	setup_requires=["cffi>=1.0.0"],
	cffi_modules=["bin/libparsing_build.py:ffibuilder"],
	install_requires=["cffi>=1.0.0"],
)

# EOF
