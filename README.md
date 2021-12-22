# CX-BUILD 
Compilation Database alternative

# Build
## Prerequisite
the CXBUILD uses linux system call trace utility called strace which was customized.
So If you want to use the cxbuild, build cstrace (cstrace prints whole path to recognize build commands, https://github.com/damho1104/strace.git).
```
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make -j8
```

When after you build 'cstrace', please copy cstrace binary into '/usr/bin' or '/bin' directory(or add $PATH environement variable) to make the cxbuild freely invokes.

## Export single portable binary
Sometimes python and python module requirements is annoying. the pyinstaller can generate everything in single binary. It is really helpful in many cases.

To do this, Required Python 3.x(we tested 3.6.9) and above version. when you ready to build the cxbuild binary, at the source root directory, type below:
```
python3 -mvenv python
source python/bin/activate
pip install wheel
pip install -r requirements.txt

pip install pyinstaller
pyinstaller build.spec
chmod +x dist/cxbuild
cp dist/cxbuild /usr/local/bin
```

----

or Just use cxbuild with python interpreter like this:

```
source env/bin/activate
pip install -r requirements.txt
python cxbuild.py capture make -j 8
```

# Usage

## Capture command

When you ready build your repository, you can use 'capture' command, to make compilation database
```
cxbuild capture [build command here]
```
If succeed, "[pwd]/.xdb/compile-commands.json" file will be generated(some intermediate file exist).


## Captured command

You can run post process only after build capture completed, It only required when debug something. 

The 'captured' command assumes that there exists trace files(full_trace.log) in .xdb directory. 
and This command run only post process phase, It will generate compile_commands.json file from full_trace.log.

```
cxbuild captured
```

# Try it
Assumes that 'cstrace' and 'cxbuild' exist in $PATH environment
```
/bin/cstrace
/bin/cxbuild
```

## gzip

Prepare source build (in Ubuntu OS, apt source command will serve source files to build):
```
$ apt source gzip
$ls -al
total 1084
drwxr-xr-x  3 minhyuk minhyuk    4096 Nov  1 10:51 .
drwxr-xr-x 12 minhyuk minhyuk    4096 Nov  1 10:51 ..
drwxr-xr-x 11 minhyuk minhyuk    4096 Nov  1 10:52 gzip-1.6
-rw-r--r--  1 minhyuk minhyuk   15604 Jul  8 01:53 gzip_1.6-5ubuntu1.1.debian.tar.xz
-rw-r--r--  1 minhyuk minhyuk    2060 Jul  8 01:53 gzip_1.6-5ubuntu1.1.dsc
-rw-r--r--  1 minhyuk minhyuk 1074924 Aug 21  2013 gzip_1.6.orig.tar.gz
```

then prepare build tools
```
$ cd gzip-1.6
$ ./configure
```

actual build will with cxbuild just type like this:
```
$ cxbuild capture make -j 8
> eXtension of Compilation Database
-- [Build]
make -j 8
cstrace -s 65535 -e trace=open,openat,execve -v -y -f -o "/home/minhyuk/cx/tests/gzip-1.6/.xdb/full_cstrace.log" -- make -j 8
  GEN      version.c
  GEN      version.h
make  all-recursive
make[1]: Entering directory '/home/minhyuk/cx/tests/gzip-1.6'
Making all in lib
make[2]: Entering directory '/home/minhyuk/cx/tests/gzip-1.6/lib'
  GEN      alloca.h
  GEN      configmake.h
  GEN      c++defs.h
  GEN      arg-nonnull.h
  GEN      warn-on-use.h
  GEN      unused-parameter.h
<...skipped...>
Making all in tests
make[2]: Entering directory '/home/minhyuk/cx/tests/gzip-1.6/tests'
make[2]: Nothing to be done for 'all'.
make[2]: Leaving directory '/home/minhyuk/cx/tests/gzip-1.6/tests'
make[1]: Leaving directory '/home/minhyuk/cx/tests/gzip-1.6'
-- [Analyzing build Activities]
/home/minhyuk/cx/tests/gzip-1.6/.xdb/xtrace_tree.json
> Finished(00:00:09)
```

Check compile_commands.json:
 ```
 $ cat .xdb/compile_commands.json
[
    {
        "directory": "/home/minhyuk/cx/tests/gzip-1.6/lib",
        "command": "gcc -D HAVE_CONFIG_H -I /home/minhyuk/cx/tests/gzip-1.6/lib -g -O2 -MT /home/minhyuk/cx/tests/gzip-1.6/lib/c-strcasecmp.o -MD -MP -MF .deps/c-strcasecmp.Tpo -c -o /home/minhyuk/cx/tests/gzip-1.6/lib/c-strcasecmp.o /home/minhyuk/cx/tests/gzip-1.6/lib/c-strcasecmp.c",
        "file": "c-strcasecmp.c"
    },
    {
        "directory": "/home/minhyuk/cx/tests/gzip-1.6/lib",
        "command": "gcc -D HAVE_CONFIG_H -I /home/minhyuk/cx/tests/gzip-1.6/lib -g -O2 -MT /home/minhyuk/cx/tests/gzip-1.6/lib/c-ctype.o -MD -MP -MF .deps/c-ctype.Tpo -c -o /home/minhyuk/cx/tests/gzip-1.6/lib/c-ctype.o /home/minhyuk/cx/tests/gzip-1.6/lib/c-ctype.c",
        "file": "c-ctype.c"
    },
    {
        "directory": "/home/minhyuk/cx/tests/gzip-1.6/lib",
        "command": "gcc -D HAVE_CONFIG_H -I /home/minhyuk/cx/tests/gzip-1.6/lib -g -O2 -MT /home/minhyuk/cx/tests/gzip-1.6/lib/cloexec.o -MD -MP -MF .deps/cloexec.Tpo -c -o /home/minhyuk/cx/tests/gzip-1.6/lib/cloexec.o /home/minhyuk/cx/tests/gzip-1.6/lib/cloexec.c",
        "file": "cloexec.c"
    },
    {
        "directory": "/home/minhyuk/cx/tests/gzip-1.6/lib",
        "command": "gcc -D HAVE_CONFIG_H -I /home/minhyuk/cx/tests/gzip-1.6/lib -g -O2 -MT /home/minhyuk/cx/tests/gzip-1.6/lib/c-strncasecmp.o -MD -MP -MF .deps/c-strncasecmp.Tpo -c -o /home/minhyuk/cx/tests/gzip-1.6/lib/c-strncasecmp.o /home/minhyuk/cx/tests/gzip-1.6/lib/c-strncasecmp.c",
        "file": "c-strncasecmp.c"
    },
    <...skipped...>
]
 ```
