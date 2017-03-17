import cffi, glob, re, tempfile, sys, os, shutil
from os.path import join, dirname, abspath

BASE       = dirname(abspath(__file__))
H_SOURCE   = open(join(BASE,"_libparsing.h")).read()
C_SOURCE   = open(join(BASE,"_libparsing.c")).read()
FFI_SOURCE = open(join(BASE,"_libparsing.ffi")).read()

def build():
	ffibuilder = cffi.FFI()
	# In order to avoid _libparsing.so: undefined symbol: PyInt_FromLong
	# SEE: http://community.activestate.com/node/9069
	# SEE: http://cffi.readthedocs.io/en/latest/embedding.html
	ffibuilder.set_source("libparsing._libparsing", H_SOURCE + C_SOURCE, extra_link_args=["-Wl,-lpcre,--export-dynamic"])
	ffibuilder.cdef(FFI_SOURCE)

	ffibuilder.embedding_init_code("""
	from my_plugin import ffi
	@ffi.def_extern()
	def module_init():
		pass
	""")

	mod_path   = dirname(abspath(__file__))
	build_path = tempfile.mkdtemp()
	ext        = ffibuilder.compile(target=mod_path + "/_libparsing.*", verbose=False, tmpdir=build_path)
	shutil.copy(ext, mod_path)
	for p in glob.glob(build_path + "/libparsing/*"): os.unlink(p)
	os.rmdir(build_path + "/libparsing")
	os.rmdir(build_path)

if __name__ == "__main__":
	args = sys.argv[1:]
	build ()
	#if args:
	#	shutil.copy("build/_libparsing.so", args[0])

# EOF - vim: syn=python ts=4 sw=4 noet
