import cffi, glob, re
from os.path import join, dirname, abspath

BASE       = dirname(abspath(__file__))
H_SOURCE   = open(join(BASE,"_libparsing.h")).read()
C_SOURCE   = open(join(BASE,"_libparsing.c")).read()
FFI_SOURCE = open(join(BASE,"_libparsing.ffi")).read()

ffibuilder = cffi.FFI()
# In order to avoid _libparsing.so: undefined symbol: PyInt_FromLong
# SEE: http://community.activestate.com/node/9069
# SEE: http://cffi.readthedocs.io/en/latest/embedding.html
ffibuilder.set_source("_libparsing", H_SOURCE + C_SOURCE, extra_link_args=["-Wl,-lpcre,--export-dynamic"])
ffibuilder.cdef(FFI_SOURCE)

ffibuilder.embedding_init_code("""
    from my_plugin import ffi

    @ffi.def_extern()
    def do_stuff(p):
        print("adding %d and %d" % (p.x, p.y))
        return p.x + p.y
""")

ffibuilder.compile(target="_libparsing.*", verbose=False, tmpdir=join(BASE,"build"))

if __name__ == "__main__":
	import sys, shutil
	args = sys.argv[1:]
	if args:
		shutil.copy("build/_libparsing.so", args[0])

# EOF - vim: syn=python ts=4 sw=4 noet
