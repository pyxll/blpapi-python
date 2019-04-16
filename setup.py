#!/usr/bin/env python

"""
setup.py file for Bloomberg Python SDK
"""

import os
import platform as plat
import re
import codecs

from sys import version
from setuptools import setup, Extension

os.chdir(os.path.dirname(os.path.realpath(__file__)))
platform = plat.system().lower()

def find_version_number():
    """Load the version number from blpapi/version.py"""
    version_path = os.path.abspath(os.path.join('blpapi', 'version.py'))
    version_file = None
    with codecs.open(version_path, 'r') as fp:
        version_file = fp.read()

    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

if version < '2.6':
    raise Exception(
        "Python versions before 2.6 are not supported (current version is "
        + version + ")")

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

if platform == 'windows':
    blpapiLibraryPath = os.path.join(blpapiRoot, 'lib')
    extraLinkArgs = ['/MANIFEST']

    # Handle the very frequent case when user need to use Visual C++ 2010
    # with Python that wants to use Visual C++ 2008.
    if plat.python_compiler().startswith('MSC v.1500'):
        if (not 'VS90COMNTOOLS' in os.environ) and \
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
    sources=['blpapi/internals_wrap.c'],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_link_args=extraLinkArgs
)

versionhelper_wrap = Extension(
    'blpapi._versionhelper',
    sources=['blpapi/versionhelper_wrap.c'],
    include_dirs=[blpapiIncludes],
    library_dirs=[blpapiLibraryPath],
    libraries=[blpapiLibraryName],
    extra_link_args=extraLinkArgs
)

setup(
    name='blpapi',
    version=find_version_number(),
    author='Bloomberg L.P.',
    author_email='open-tech@bloomberg.net',
    description='Python SDK for Bloomberg BLPAPI',
    ext_modules=[blpapi_wrap, versionhelper_wrap],
    url='http://www.bloomberglabs.com/api/',
    packages=["blpapi"],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: Other/Proprietary License',
        'Topic :: Office/Business :: Financial',
    ],
)
