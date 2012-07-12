#!/usr/bin/python
"""Fabric deployment helper functions"""
# pylint: disable=W0402,W0801

import inspect
import os
import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

ROOT = os.path.dirname(inspect.getfile(inspect.currentframe()))
with open(os.path.join(ROOT, 'README')) as readme:
    long_description = readme.read()

classifiers = """
Development Status :: 3 - Alpha
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Topic :: Software Development :: Build Tools
Topic :: System :: Installation/Setup
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
"""

classifiers = [c.strip() for c in classifiers.split('\n') if c.strip()]

setup(
    name="fablib",
    author="Graham Poulter",
    author_email="graham.poulter@gmail.com",
    classifiers=classifiers,
    description=__doc__,
    license='MIT',
    long_description=long_description,
    py_modules=['fablib'],
    url='http://github.com/gpoulter/fablib',
    version="0.1.0",
)
