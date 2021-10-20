# -*- mode: python -*-

block_cipher = None

import subprocess
import time
try:
    #git_rev = subprocess.check_output(["git", "describe", "--always"]).strip().decode('ascii')
    git_rev = subprocess.check_output(["git", "describe", "--tags"]).strip().decode('ascii')
    #git_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('ascii')
    #if git_branch == 'master':
    #    git_rev = subprocess.check_output(["git", "describe", "--tags"]).strip().decode('ascii')
    #else:
    #    commit_sha = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('ascii')
    #    git_rev = f'{git_branch}-{commit_sha}'
    with open('version.py', 'w') as version_file:
        version_file.write('VERSION = "[v%s-%s]"' % (time.strftime("%y%m%d%H"), git_rev))

    print(">>>> ")
    print("--------- GIT REV: %s -----------" % git_rev)
    print(">>>> ")

except:
    with open('version.py', 'w') as version_file:
        version_file.write('VERSION = "[v%s-%s]"' % (time.strftime("%y%m%d%H"), "LOCAL"))


old_path = os.environ['PATH']
if os.name == 'nt':
    os.environ['PATH'] = r'C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x86' + os.pathsep + os.environ.get('PATH')



def package(program):
    a = Analysis(['%s.py' % program],
                 binaries=[],
                 datas=[],
                 hiddenimports=[],
                 hookspath=[],
                 runtime_hooks=[],
                 excludes=[],
                 win_no_prefer_redirects=False,
                 win_private_assemblies=False,
                 cipher=block_cipher)
    pyz = PYZ(a.pure, a.zipped_data,
                 cipher=block_cipher)
    exe = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              name=program,
              debug=False,
              strip=False,
              upx=True,
              icon='icon.ico',
              runtime_tmpdir=None,
              console=True )


package('cxbuild')
