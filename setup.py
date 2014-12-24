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
import os, tempfile

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

LONG_DESCRIPTION = "\n".join(_[2:].strip() for _ in file("src/parsing.h").read().decode("utf-8").split("[START:INTRO]",1)[1].split("[END:INTRO]")[0].split("\n"))

# If pandoc is installed, we translate the documentation to RST
if os.popen("which pandoc").read():
	p = tempfile.mktemp()
	with file(p,"w") as f: f.write(LONG_DESCRIPTION)
	LONG_DESCRIPTION = os.popen("pandoc -f markdown -t rst %s" % (p)).read()
	print LONG_DESCRIPTION
	os.unlink(p)

setup(
	name             = "libparsing",
	version          = (l.split('"')[1] for l in file("src/parsing.h").readlines() if l.startswith("#define __PARSING_VERSION__")).next(),
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
		("libparsing", ("python/cdoclib.py", "src/parsing.c", "src/parsing.h", "src/oo.h"))
	],
	ext_modules = [libparsing],
)

# EOF
