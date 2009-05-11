#!/usr/bin/env python
from distutils.core import setup
setup(
    name='typepad',
    version='1.0',
    description='TypePad API SDK',
    author='Six Apart',
    author_email='python@sixapart.com',
    url='http://code.sixapart.com/svn/typepad-py/',

    packages=['typepad'],
    provides=['typepad'],
    requires=['oauth', 'remoteobjects', 'batchhttp'],
)
