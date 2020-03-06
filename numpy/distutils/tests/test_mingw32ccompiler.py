import shutil
import subprocess
import sys
import pytest

from numpy.distutils import mingw32ccompiler


@pytest.mark.skipif(sys.platform != 'win32', reason='win32 only test')
def test_build_import():
    # make sure `nm.exe` exists and supports the current python version. This
    # can get mixed up when the PATH has a 64-bit nm but the python is 32-bit
    try:
        out = subprocess.check_output(['nm.exe', '--help'])
    except FileNotFoundError:
        pytest.skip("'nm.exe' not on path, is mingw installed?")
    supported = out[out.find(b'supported targets:'):]
    if sys.maxsize < 2**32 and b'pe-i386' not in supported:
            raise ValueError("'nm.exe' found but it does not support 32-bit"
                             "dlls when using 32-bit python")
    elif b'pe-x86-64' not in supported:
            raise ValueError("'nm.exe' found but it does not support 64-bit"
                             "dlls when using 64-bit python")
    # Hide the import library to force it being built
    has_import_lib, fullpath = mingw32ccompiler._check_for_import_lib()
    if has_import_lib: 
        shutil.move(fullpath, fullpath + '.bak')

    try: 
        # Whew, now we can actually test the function
        mingw32ccompiler.build_import_library()
    finally:
        if has_import_lib:
            shutil.move(fullpath + '.bak', fullpath)
