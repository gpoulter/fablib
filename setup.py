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

try:
    from setuptools import setup
except:
    from distutils.core import setup

setup(
    name="fablib",
    author="Graham Poulter",
    description=__doc__,
    py_modules=['fablib'],
    version="0.1.0",
)
