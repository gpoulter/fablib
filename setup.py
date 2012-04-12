"""Fabric deployment helper functions"""

from distutils.core import setup
from fablib import __version__

setup(
    name="fablib",
    version=__version__,
    description=__doc__,
    author="Graham Poulter",
    author_email="graham@mocality.com",
    py_modules=['fablib'],
)
