"""Fabric deployment helper functions"""
# pylint: disable=W0402

try:
    from setuptools import setup
except:
    from distutils.core import setup

setup(
    name="fablib",
    version="0.1.0",
    description=__doc__,
    author="Graham Poulter",
    author_email="graham@mocality.com",
    py_modules=['fablib'],
)
