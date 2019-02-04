#!/usr/bin/env python

"""
setup.py file for Bloomberg Python SDK
"""

from setuptools import setup, Extension
import os
import platform as plat
from sys import version

os.chdir(os.path.dirname(os.path.realpath(__file__)))
platform = plat.system().lower()
versionString = '3.12.2'

if version < '2.6':
    raise Exception(
        "Python versions before 2.6 are not supported (current version is " +
	version + ")")

blpapiRoot = os.environ.get('BLPAPI_ROOT')
blpapiIncludesVar = os.environ.get('BLPAPI_INCDIR')
blpapiLibVar = os.environ.get('BLPAPI_LIBDIR')

assert blpapiRoot or (blpapiIncludesVar and blpapiLibVar), \
        "BLPAPI_ROOT environment variable isn't defined"

is64bit = plat.architecture()[0] == '64bit'
if is64bit:
    blpapiLibraryName = 'blpapi3_64'
else:
    blpapiLibraryName = 'blpapi3_32'

cmdclass = {}
if platform == 'windows':
    from distutils.command import build_ext
    from ctypes import windll, create_string_buffer, c_uint, byref, string_at, wstring_at, c_void_p
    import shutil
    import array
    import re

    class BuildBlpExtension(build_ext.build_ext):
        @staticmethod
        def get_file_info(filename, info):
            """
            Extract information from a file.
            """
            if version >= '3.0':
                GetFileVersionInfoSize = windll.version.GetFileVersionInfoSizeW
                GetFileVersionInfo =  windll.version.GetFileVersionInfoW
                VerQueryValue = windll.version.VerQueryValueW
                tstring_at = wstring_at
            else:
                GetFileVersionInfoSize = windll.version.GetFileVersionInfoSizeA
                GetFileVersionInfo = windll.version.GetFileVersionInfoA
                VerQueryValue = windll.version.VerQueryValueA
                tstring_at = string_at

            # Get size needed for buffer (0 if no info)
            size = GetFileVersionInfoSize(filename, None)
            if not size:
                return ''

            # Create buffer
            res = create_string_buffer(size)

            # Load file informations into buffer res
            GetFileVersionInfo(filename, None, size, res)
            r = c_void_p()
            l = c_uint()

            # Look for codepages
            VerQueryValue(res, '\\VarFileInfo\\Translation', byref(r), byref(l))

            # If no codepage -> empty string
            if not l.value:
                return ''

            # Take the first codepage
            codepages = array.array('H', string_at(r.value, l.value))
            codepage = tuple(codepages[:2].tolist())

            # Extract information
            VerQueryValue(res, ('\\StringFileInfo\\%04x%04x\\' + info) % codepage, byref(r), byref(l))
            return tstring_at(r.value, l.value-1).replace(" ", "").replace(",", ".")

        def build_extension(self, ext):
            """
            Builds the C extension libraries, but replaces blpapi dll dependency with
            a versioned copy so it doesn't conflict with other Bloomberg tools.
            """
            # Replace blpapiLibraryName with the version specific one
            if blpapiLibraryName in ext.libraries:
                srcdll = os.path.join(blpapiLibraryPath, blpapiLibraryName + ".dll")
                version = self.get_file_info(srcdll, "FileVersion")
                versionedLibName = blpapiLibraryName + "_" + version
                build_dir = os.path.dirname(self.get_ext_fullpath(ext.name))

                if self.force or not os.path.exists(os.path.join(self.build_temp, versionedLibName + ".lib")):
                    if not self.compiler.initialized:
                        self.compiler.initialize()

                    if not os.path.exists(self.build_temp):
                        os.makedirs(self.build_temp)

                    # dump the def file for the dll to rebuild the lib file
                    dumpbinfile = os.path.join(self.build_temp, blpapiLibraryName + "_" + version + ".dumpbin")
                    dumpbin = os.path.join(os.path.dirname(self.compiler.lib), "DUMPBIN.EXE")
                    self.compiler.spawn([dumpbin, "/EXPORTS", "/OUT:" + dumpbinfile,  srcdll])

                    # get all the function definitions
                    deffile = os.path.join(self.build_temp, blpapiLibraryName + "_" + version + ".def")
                    with open(deffile, "wt") as out_fh:
                        exports = []
                        for line in open(dumpbinfile).readlines():
                            matches = re.search(r'^\s*(\d+)\s+[A-Z0-9]+\s+[A-Z0-9]{8}\s+([^ ]+)', line)
                            if matches:
                                exports.append(matches.group(2) + "\n")
                        out_fh.writelines(["EXPORTS\n"] + exports)

                    # rebuild the lib file with the new dll name
                    libfile = os.path.join(self.build_temp, blpapiLibraryName + "_" + version + ".lib")
                    machine = "/MACHINE:" + ("X64" if is64bit else "X86")
                    self.compiler.spawn([self.compiler.lib, machine, "/DEF:" + deffile, "/OUT:" + libfile])

                # copy the versioned dll the the build output
                if self.force or not os.path.exists(os.path.join(build_dir, versionedLibName + ".dll")):
                    if not os.path.exists(build_dir):
                        os.makedirs(build_dir)
                    shutil.copy(os.path.join(blpapiLibraryPath, blpapiLibraryName + ".dll"),
                                os.path.join(build_dir, versionedLibName + ".dll"))

                # replace blpapi.lib with the versioned one
                ext.libraries = [versionedLibName if x == blpapiLibraryName else x for x in ext.libraries]
                ext.library_dirs.insert(0, self.build_temp)

            build_ext.build_ext.build_extension(self, ext)

    cmdclass.update({
         "build_ext": BuildBlpExtension,
    })

    blpapiLibraryPath = os.path.join(blpapiRoot, 'lib')
    extraLinkArgs = ['/MANIFEST']

    # Handle the very frequent case when user need to use Visual C++ 2010
    # with Python that wants to use Visual C++ 2008.
    if plat.python_compiler().startswith('MSC v.1500'):
        if (not ('VS90COMNTOOLS' in os.environ)) and \
                ('VS100COMNTOOLS' in os.environ):
            os.environ['VS90COMNTOOLS'] = os.environ['VS100COMNTOOLS']
elif platform == 'linux':
    blpapiLibraryPath = os.path.join(blpapiRoot, 'Linux')
    extraLinkArgs = []
elif platform == 'darwin':
    blpapiLibraryPath = os.path.join(blpapiRoot, 'Darwin')
    extraLinkArgs = []
else:
    raise Exception("Platform '" + platform + "' isn't supported")



blpapiLibraryPath = blpapiLibVar or blpapiLibraryPath
blpapiIncludes = blpapiIncludesVar or os.path.join(blpapiRoot, 'include')

blpapi_wrap = Extension(
    'blpapi._internals',
    sources=['blpapi/internals_wrap.cxx'],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_link_args=extraLinkArgs
)

versionhelper_wrap = Extension(
    'blpapi._versionhelper',
    sources=['blpapi/versionhelper_wrap.cxx'],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_link_args=extraLinkArgs
)

setup(
    name='blpapi',
    version=versionString,
    author='Bloomberg L.P.',
    author_email='open-tech@bloomberg.net',
    description='Python SDK for Bloomberg BLPAPI',
    ext_modules=[blpapi_wrap, versionhelper_wrap],
    url='http://www.bloomberglabs.com/api/',
    packages=["blpapi"],
    cmdclass=cmdclass,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: Other/Proprietary License',
        'Topic :: Office/Business :: Financial',
    ],
)
