from contextlib import contextmanager
import os
import os.path
from shutil import rmtree
import tempfile
import zipfile

from fabric.api import *
from httplib2 import Http


def fill_environment():
    env.name = local('python setup.py --name').strip()
    env.version = local('python setup.py --version').strip()

def sdist():
    local('python setup.py sdist')

@contextmanager
def _download_source(server, path):
    http = Http()
    resp, cont = http.request(''.join((server, path)))
    if resp.status != 200:
        abort('Unexpected %d result fetching nouns.json')

    with tempfile.NamedTemporaryFile() as source_file:
        source_file.write(cont)
        source_file.flush()
        yield source_file.name

def regenerate(server=None):
    if server is None:
        server = 'http://api.typepad.com/'

    with _download_source(server, 'nouns.json') as nouns_filename:
        with _download_source(server, 'object-types.json') as types_filename:
            # generate a new typepad/api.py
            local('python generate.py --nouns %s --types %s typepad/api.py' % (nouns_filename, types_filename), capture=False)

            # generate a new docs section
            #local('python generate.py --nouns %s --types %s --docs typepad/doc/api/' % (nouns_filename, types_filename))

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
