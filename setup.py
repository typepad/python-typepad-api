#!/usr/bin/env python
from setuptools import setup
setup(
    name='typepad',
    version='1.0',
    description='TypePad API SDK',
    packages=['typepad'],
    package_dir={'typepad': '.'},

    install_requires=['remoteobjects', 'oauth', 'batchhttp'],
    provides=['typepad'],

    author='Six Apart',
    author_email='python@sixapart.com',
    url='http://code.sixapart.com/svn/typepad-py/',
)
