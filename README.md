# CX-BUILD 
Compilation Database alternative

# Build
```
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make -j8
```

At the source root directory, type below:
```
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build.spec --hidden-import=fcntl --hidden-import=gitPython
cp dist/cxbuild /usr/local/bin
```

