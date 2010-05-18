from contextlib import contextmanager
import os
from os.path import join, dirname, abspath
import re
from shutil import rmtree
import tempfile
import zipfile

from fabric.api import *
from httplib2 import Http


def fill_environment():
    env.dist_name = local('python setup.py --name').strip()
    env.dist_version = local('python setup.py --version').strip()

def check_active_package():
    require('dist_name')

    # Are we set up to be us?
    py_file = abspath(local("python -c 'import %(dist_name)s; print %(dist_name)s.__file__'" % env).strip())
    if dirname(py_file) != join(dirname(abspath(__file__)), env.dist_name):
        abort("The local %(dist_name)s package is not the %(dist_name)s package in the active environment: %(badpath)s"
            % {'dist_name': env.dist_name, 'badpath': dirname(py_file)})

def check_version(ver):
    require('dist_name', 'dist_version')

    # 1. the setup.py version
    if env.dist_version != ver:
        abort("Version in setup.py is %r, not %r" % (env.dist_version, ver))

    # 2. the __init__.py version
    py_ver = local("python -c 'import %(dist_name)s; print %(dist_name)s.__version__'" % env).strip()
    if py_ver != ver:
        abort("Version in %s/__init__.py is %r, not %r" % (env.dist_name, py_ver, ver))

    # 3. the doc/conf.py version
    doc_ver = local("""python -c 'data = {}; execfile("doc/conf.py", data); print data["release"]'""").strip()
    if doc_ver != ver:
        abort("Release version in doc/conf.py is %r, not %r" % (doc_ver, ver))

def check_changes(ver):
    # Is our version already in CHANGES.rst?
    with open('CHANGES.rst') as changes_file:
        found = False
        for line in changes_file:
            if re.match(r'^%s\b' % re.escape(ver), line):
                found = True
                break
        if not found:
            abort("Version %s doesn't appear in the CHANGES.rst" % (ver,))

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
    if not server.startswith('http'):
        server = 'http://%s' % server
    if not server.endswith('/'):
        server = '%s/' % server

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
                zip.write(join(root, filename))
    finally:
        rmtree(target_dir)

def package(ver):
    fill_environment()

    check_active_package()
    check_version(ver)
    check_changes(ver)

    # TODO: check that we needn't regenerate the python module again?

    # rebuild the README
    local('python doc/readme_from_docstring.py')

    sdist()  # makes dist/name-version.tar.gz
    docs('dist/%(dist_name)s-%(dist_version)s-docs.zip' % env)
