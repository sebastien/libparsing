import cffi, glob, re, tempfile, sys, os, shutil
from os.path import join, dirname, abspath

__doc__ = """
Builds a native CFFI version of libparsing using the sources included in the
module.
"""

NAME       = "_libparsing"
BASE       = dirname(abspath(__file__))
H_SOURCE   = open(join(BASE,NAME + ".h")).read()
C_SOURCE   = open(join(BASE,NAME + ".c")).read()
FFI_SOURCE = open(join(BASE,NAME + ".ffi")).read()
PY_VERSION = "{0}_{1}".format(sys.version_info.major, sys.version_info.minor)

def name():
	"""Returns the name of the Python module to be built"""
	return "{0}py{1}".format(NAME, PY_VERSION)

def filename(ext):
	"""Returns the filename of the Python module to be built"""
	return "{0}py{1}.{2}".format(NAME, PY_VERSION, ext)

def build(path=BASE):
	"""Builds a native Python module/extension using CFFI. The extension will
	be available at `{base}/{name}py{version}.{so|dylib|dll}`."""

	# In order to avoid _libparsing.so: undefined symbol: PyInt_FromLong
	# SEE: http://community.activestate.com/node/9069
	# SEE: http://cffi.readthedocs.io/en/latest/embedding.html
	ffibuilder = cffi.FFI()
	ffibuilder.set_source(
		"{0}".format(name()), H_SOURCE + C_SOURCE,
		extra_link_args=["-Wl,-lpcre,--export-dynamic"]
	)
	ffibuilder.cdef(FFI_SOURCE)
	ffibuilder.embedding_init_code("""
	from {0} import ffi
	@ffi.def_extern()
	def module_init():
		pass
	""".format(name()))

	# Now we get the destination moduled path and build the module
	mod_path   = dirname(abspath(__file__))
	build_path = tempfile.mkdtemp()
	ext        = ffibuilder.compile(verbose=False, tmpdir=build_path)
	dest       = os.path.join(path, os.path.basename(ext))

	# We move the built extension to the given directory and we return
	# the built extension path.
	shutil.move(ext, dest)
	for p in glob.glob(build_path + "/*.*"): os.unlink(p)
	os.rmdir(build_path)
	return dest

if __name__ == "__main__":
	args = sys.argv[1:]
	build ()
	#if args:
	#	shutil.copy("build/_libparsing.so", args[0])

# EOF - vim: syn=python ts=4 sw=4 noet
