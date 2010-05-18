import os
import os.path
from shutil import rmtree
import tempfile
import zipfile

from fabric.api import *


def fill_environment():
    env.name = local('python setup.py --name').strip()
    env.version = local('python setup.py --version').strip()

def sdist():
    local('python setup.py sdist')

def docs(zipname):
    target_dir = tempfile.mkdtemp()
    try:
        local('sphinx-build -E doc %s' % (target_dir,), capture=False)

        # Also zip them up.
        zip = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(target_dir):
            for filename in files:
                zip.write(os.path.join(root, filename))
    finally:
        rmtree(target_dir)
