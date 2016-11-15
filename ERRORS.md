*** Error in `/usr/bin/python': corrupted double-linked list: 0x0000000000bfa020 ***
======= Backtrace: =========
/lib/x86_64-linux-gnu/libc.so.6(+0x777e5)[0x7f06013317e5]
/lib/x86_64-linux-gnu/libc.so.6(+0x7e6f8)[0x7f06013386f8]
/lib/x86_64-linux-gnu/libc.so.6(+0x800a8)[0x7f060133a0a8]
/lib/x86_64-linux-gnu/libc.so.6(cfree+0x4c)[0x7f060133d98c]
/usr/bin/python[0x4b5605]
/usr/bin/python(PyDict_SetItem+0x442)[0x4a0f22]
/usr/bin/python(_PyModule_Clear+0x133)[0x502bc3]
/usr/bin/python(PyImport_Cleanup+0x26f)[0x5027ef]
/usr/bin/python(Py_Finalize+0x89)[0x500459]
/usr/bin/python(Py_Main+0x46f)[0x49e14f]
/lib/x86_64-linux-gnu/libc.so.6(__libc_start_main+0xf0)[0x7f06012da830]
/usr/bin/python(_start+0x29)[0x49dbf9]
======= Memory map: ========
00400000-006e9000 r-xp 00000000 08:02 533458                             /usr/bin/python2.7
008e9000-008eb000 r--p 002e9000 08:02 533458                             /usr/bin/python2.7
008eb000-00962000 rw-p 002eb000 08:02 533458                             /usr/bin/python2.7
00962000-00985000 rw-p 00000000 00:00 0 
00b3e000-00d74000 rw-p 00000000 00:00 0                                  [heap]
7f05f8000000-7f05f8021000 rw-p 00000000 00:00 0 
7f05f8021000-7f05fc000000 ---p 00000000 00:00 0 
7f05fe653000-7f05fe669000 r-xp 00000000 08:02 1315999                    /lib/x86_64-linux-gnu/libgcc_s.so.1
7f05fe669000-7f05fe868000 ---p 00016000 08:02 1315999                    /lib/x86_64-linux-gnu/libgcc_s.so.1
7f05fe868000-7f05fe869000 rw-p 00015000 08:02 1315999                    /lib/x86_64-linux-gnu/libgcc_s.so.1
7f05fe869000-7f05fe929000 rw-p 00000000 00:00 0 
7f05fe929000-7f05fec1b000 r-xp 00000000 08:02 524302                     /usr/lib/x86_64-linux-gnu/libpython2.7.so.1.0
7f05fec1b000-7f05fee1b000 ---p 002f2000 08:02 524302                     /usr/lib/x86_64-linux-gnu/libpython2.7.so.1.0
7f05fee1b000-7f05fee1d000 r--p 002f2000 08:02 524302                     /usr/lib/x86_64-linux-gnu/libpython2.7.so.1.0
7f05fee1d000-7f05fee94000 rw-p 002f4000 08:02 524302                     /usr/lib/x86_64-linux-gnu/libpython2.7.so.1.0
7f05fee94000-7f05feeb7000 rw-p 00000000 00:00 0 
7f05feeb7000-7f05fef25000 r-xp 00000000 08:02 1316090                    /lib/x86_64-linux-gnu/libpcre.so.3.13.2
7f05fef25000-7f05ff125000 ---p 0006e000 08:02 1316090                    /lib/x86_64-linux-gnu/libpcre.so.3.13.2
7f05ff125000-7f05ff126000 r--p 0006e000 08:02 1316090                    /lib/x86_64-linux-gnu/libpcre.so.3.13.2
7f05ff126000-7f05ff127000 rw-p 0006f000 08:02 1316090                    /lib/x86_64-linux-gnu/libpcre.so.3.13.2
7f05ff127000-7f05ff132000 r-xp 00000000 00:2c 11014822                   /home/sebastien/Projects/Public/libparsing/src/python/libparsing/__libparsing.so
7f05ff132000-7f05ff332000 ---p 0000b000 00:2c 11014822                   /home/sebastien/Projects/Public/libparsing/src/python/libparsing/__libparsing.so
7f05ff332000-7f05ff333000 rw-p 0000b000 00:2c 11014822                   /home/sebastien/Projects/Public/libparsing/src/python/libparsing/__libparsing.so
7f05ff333000-7f05ff373000 rw-p 00000000 00:00 0 
7f05ff373000-7f05ff37f000 r-xp 00000000 08:02 668276                     /usr/lib/python2.7/lib-dynload/_json.x86_64-linux-gnu.so
7f05ff37f000-7f05ff57e000 ---p 0000c000 08:02 668276                     /usr/lib/python2.7/lib-dynload/_json.x86_64-linux-gnu.so
7f05ff57e000-7f05ff57f000 r--p 0000b000 08:02 668276                     /usr/lib/python2.7/lib-dynload/_json.x86_64-linux-gnu.so
7f05ff57f000-7f05ff580000 rw-p 0000c000 08:02 668276                     /usr/lib/python2.7/lib-dynload/_json.x86_64-linux-gnu.so
7f05ff580000-7f05ff600000 rw-p 00000000 00:00 0 
7f05ff600000-7f05ff606000 r-xp 00000000 08:02 668286                     /usr/lib/python2.7/lib-dynload/_hashlib.x86_64-linux-gnu.so
7f05ff606000-7f05ff805000 ---p 00006000 08:02 668286                     /usr/lib/python2.7/lib-dynload/_hashlib.x86_64-linux-gnu.so
7f05ff805000-7f05ff806000 r--p 00005000 08:02 668286                     /usr/lib/python2.7/lib-dynload/_hashlib.x86_64-linux-gnu.so
7f05ff806000-7f05ff807000 rw-p 00006000 08:02 668286                     /usr/lib/python2.7/lib-dynload/_hashlib.x86_64-linux-gnu.so
7f05ff807000-7f05ff908000 rw-p 00000000 00:00 0 
7f05ff908000-7f05ffb22000 r-xp 00000000 08:02 1343778                    /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
7f05ffb22000-7f05ffd21000 ---p 0021a000 08:02 1343778                    /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
7f05ffd21000-7f05ffd3d000 r--p 00219000 08:02 1343778                    /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
7f05ffd3d000-7f05ffd49000 rw-p 00235000 08:02 1343778                    /lib/x86_64-linux-gnu/libcrypto.so.1.0.0
7f05ffd49000-7f05ffd4c000 rw-p 00000000 00:00 0 
7f05ffd4c000-7f05ffdaa000 r-xp 00000000 08:02 1343799                    /lib/x86_64-linux-gnu/libssl.so.1.0.0
7f05ffdaa000-7f05fffaa000 ---p 0005e000 08:02 1343799                    /lib/x86_64-linux-gnu/libssl.so.1.0.0
7f05fffaa000-7f05fffae000 r--p 0005e000 08:02 1343799                    /lib/x86_64-linux-gnu/libssl.so.1.0.0
7f05fffae000-7f05fffb5000 rw-p 00062000 08:02 1343799                    /lib/x86_64-linux-gnu/libssl.so.1.0.0
7f05fffb5000-7f05fffca000 r-xp 00000000 08:02 668294                     /usr/lib/python2.7/lib-dynload/_ssl.x86_64-linux-gnu.so
7f05fffca000-7f06001c9000 ---p 00015000 08:02 668294                     /usr/lib/python2.7/lib-dynload/_ssl.x86_64-linux-gnu.so
7f06001c9000-7f06001ca000 r--p 00014000 08:02 668294                     /usr/lib/python2.7/lib-dynload/_ssl.x86_64-linux-gnu.so
7f06001ca000-7f06001ce000 rw-p 00015000 08:02 668294                     /usr/lib/python2.7/lib-dynload/_ssl.x86_64-linux-gnu.so
7f06001ce000-7f060020e000 rw-p 00000000 00:00 0 
7f060020e000-7f0600215000 r-xp 00000000 08:02 535345                     /usr/lib/x86_64-linux-gnu/libffi.so.6.0.4
7f0600215000-7f0600414000 ---p 00007000 08:02 535345                     /usr/lib/x86_64-linux-gnu/libffi.so.6.0.4
7f0600414000-7f0600415000 r--p 00006000 08:02 535345                     /usr/lib/x86_64-linux-gnu/libffi.so.6.0.4
7f0600415000-7f0600416000 rw-p 00007000 08:02 535345                     /usr/lib/x86_64-linux-gnu/libffi.so.6.0.4
7f0600416000-7f0600434000 r-xp 00000000 08:02 668303                     /usr/lib/python2.7/lib-dynload/_ctypes.x86_64-linux-gnu.so
7f0600434000-7f0600633000 ---p 0001e000 08:02 668303                     /usr/lib/python2.7/lib-dynload/_ctypes.x86_64-linux-gnu.so
7f0600633000-7f0600634000 r--p 0001d000 08:02 668303                     /usr/lib/python2.7/lib-dynload/_ctypes.x86_64-linux-gnu.so
7f0600634000-7f0600638000 rw-p 0001e000 08:02 668303                     /usr/lib/python2.7/lib-dynload/_ctypes.x86_64-linux-gnu.so
7f0600638000-7f06006b8000 rw-p 00000000 00:00 0 
7f06006b8000-7f0600990000 r--p 00000000 08:02 524497                     /usr/lib/locale/locale-archive
7f0600990000-7f0600a98000 r-xp 00000000 08:02 1328877                    /lib/x86_64-linux-gnu/libm-2.23.so
7f0600a98000-7f0600c97000 ---p 00108000 08:02 1328877                    /lib/x86_64-linux-gnu/libm-2.23.so
7f0600c97000-7f0600c98000 r--p 00107000 08:02 1328877                    /lib/x86_64-linux-gnu/libm-2.23.so
7f0600c98000-7f0600c99000 rw-p 00108000 08:02 1328877                    /lib/x86_64-linux-gnu/libm-2.23.so
7f0600c99000-7f0600cb2000 r-xp 00000000 08:02 1316152                    /lib/x86_64-linux-gnu/libz.so.1.2.8
7f0600cb2000-7f0600eb1000 ---p 00019000 08:02 1316152                    /lib/x86_64-linux-gnu/libz.so.1.2.8
7f0600eb1000-7f0600eb2000 r--p 00018000 08:02 1316152                    /lib/x86_64-linux-gnu/libz.so.1.2.8
7f0600eb2000-7f0600eb3000 rw-p 00019000 08:02 1316152                    /lib/x86_64-linux-gnu/libz.so.1.2.8
7f0600eb3000-7f0600eb5000 r-xp 00000000 08:02 1328879                    /lib/x86_64-linux-gnu/libutil-2.23.so
7f0600eb5000-7f06010b4000 ---p 00002000 08:02 1328879                    /lib/x86_64-linux-gnu/libutil-2.23.so
7f06010b4000-7f06010b5000 r--p 00001000 08:02 1328879                    /lib/x86_64-linux-gnu/libutil-2.23.so
7f06010b5000-7f06010b6000 rw-p 00002000 08:02 1328879                    /lib/x86_64-linux-gnu/libutil-2.23.so
7f06010b6000-7f06010b9000 r-xp 00000000 08:02 1328886                    /lib/x86_64-linux-gnu/libdl-2.23.so
7f06010b9000-7f06012b8000 ---p 00003000 08:02 1328886                    /lib/x86_64-linux-gnu/libdl-2.23.so
7f06012b8000-7f06012b9000 r--p 00002000 08:02 1328886                    /lib/x86_64-linux-gnu/libdl-2.23.so
7f06012b9000-7f06012ba000 rw-p 00003000 08:02 1328886                    /lib/x86_64-linux-gnu/libdl-2.23.so
7f06012ba000-7f0601479000 r-xp 00000000 08:02 1328885                    /lib/x86_64-linux-gnu/libc-2.23.so
7f0601479000-7f0601679000 ---p 001bf000 08:02 1328885                    /lib/x86_64-linux-gnu/libc-2.23.so
7f0601679000-7f060167d000 r--p 001bf000 08:02 1328885                    /lib/x86_64-linux-gnu/libc-2.23.so
7f060167d000-7f060167f000 rw-p 001c3000 08:02 1328885                    /lib/x86_64-linux-gnu/libc-2.23.so
7f060167f000-7f0601683000 rw-p 00000000 00:00 0 
7f0601683000-7f060169b000 r-xp 00000000 08:02 1328884                    /lib/x86_64-linux-gnu/libpthread-2.23.so
7f060169b000-7f060189a000 ---p 00018000 08:02 1328884                    /lib/x86_64-linux-gnu/libpthread-2.23.so
7f060189a000-7f060189b000 r--p 00017000 08:02 1328884                    /lib/x86_64-linux-gnu/libpthread-2.23.so
7f060189b000-7f060189c000 rw-p 00018000 08:02 1328884                    /lib/x86_64-linux-gnu/libpthread-2.23.so
7f060189c000-7f06018a0000 rw-p 00000000 00:00 0 
7f06018a0000-7f06018c6000 r-xp 00000000 08:02 1328881                    /lib/x86_64-linux-gnu/ld-2.23.so
7f06018ec000-7f06019ac000 rw-p 00000000 00:00 0 
7f06019dd000-7f0601aa2000 rw-p 00000000 00:00 0 
7f0601ab1000-7f0601ab2000 rw-p 00000000 00:00 0 
7f0601ab2000-7f0601ac3000 rwxp 00000000 00:00 0 
7f0601ac3000-7f0601ac5000 rw-p 00000000 00:00 0 
7f0601ac5000-7f0601ac6000 r--p 00025000 08:02 1328881                    /lib/x86_64-linux-gnu/ld-2.23.so
7f0601ac6000-7f0601ac7000 rw-p 00026000 08:02 1328881                    /lib/x86_64-linux-gnu/ld-2.23.so
7f0601ac7000-7f0601ac8000 rw-p 00000000 00:00 0 
7ffc55eec000-7ffc55f0e000 rw-p 00000000 00:00 0                          [stack]
7ffc55fd5000-7ffc55fd7000 r--p 00000000 00:00 0                          [vvar]
7ffc55fd7000-7ffc55fd9000 r-xp 00000000 00:00 0                          [vdso]
ffffffffff600000-ffffffffff601000 r-xp 00000000 00:00 0                  [vsyscall]


Parsing: 0..*(hello world)
python: malloc.c:2392: sysmalloc: Assertion `(old_top == initial_top (av) && old_size == 0) || ((unsigned long) (old_size) >= MINSIZE && prev_inuse (old_top) && ((unsigned long) old_end & (pagesize - 1)) == 0)' failed.

