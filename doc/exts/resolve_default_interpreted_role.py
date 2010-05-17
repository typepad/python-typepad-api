# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""

A Sphinx extension to resolve default interpreted roles (aka title references)
into cross-references.

"""


from docutils.nodes import NodeVisitor, SparseNodeVisitor, literal
import re

from sphinx.addnodes import desc, desc_signature, desc_addname, pending_xref


DESCTYPE_TO_REFTYPE = {
    'function': 'func',
    'method': 'meth',
    'attribute': 'attr',
}


class DefaultInterpreter(SparseNodeVisitor):

    def __init__(self, app, document, docname):
        SparseNodeVisitor.__init__(self, document)
        self.app = app
        self.docname = docname
        self.desc_scope = []
        self.new_pending_refs = False

    def visit_desc(self, node):
        addnames = node.traverse(desc_addname)
        if addnames:
            self.desc_scope.append(addnames[0].astext()[:-1])
        else:
            self.desc_scope.append(None)

    def depart_desc(self, node):
        self.desc_scope.pop()

    def depart_title_reference(self, node):
        builder = self.app.builder
        env = builder.env
        supertree = node.parent

        # Try finding the reference conventionally, based on what "desc"
        # blocks we're inside.
        nodetext = node.children[0].astext()
        for maybe_scope in self.desc_scope:
            if maybe_scope is None:
                continue
            # find_desc() doesn't actually care about the type
            # of plain descs, as long as it's not a c-something.
            name, desc = env.find_desc(maybe_scope, None, nodetext, 'something')
            if desc is not None:
                return self.crossreference_title_ref(node, name, desc[1])

        # Brute force through all known descrefs.
        name_suf = re.compile(r'(?: \A | \. ) %s \Z' % (re.escape(nodetext),),
            re.VERBOSE | re.MULTILINE | re.DOTALL)
        cands = [(name, desc[1]) for name, desc in env.descrefs.iteritems()
            if name_suf.search(name)]

        if len(cands) > 1:
            self.document.reporter.warning('Multiple references found for %r: %s'
                % (nodetext, ', '.join(name for name, desc_type in cands)))
            return
        elif cands:
            return self.crossreference_title_ref(node, *cands[0])

        # Brute force through all intersphinx data (if any).
        if not hasattr(env, 'intersphinx_inventory'):
            return
        allcands = [(name, isref[0], isref[1] == 'Python')
            for name, isref in env.intersphinx_inventory.iteritems()
            if name_suf.search(name)]
        pycands = [(name, desc_type) for name, desc_type, is_py in allcands if is_py]
        othercands = [(name, desc_type) for name, desc_type, is_py in allcands if not is_py]

        # Prefer non-Python references to things in the standard library.
        for cands in (othercands, pycands):
            if len(cands) > 1:
                self.document.reporter.warning('Multiple references found for %r: %s'
                    % (nodetext, ', '.join(name for name, desc_type in cands)))
                return
            elif cands:
                return self.crossreference_title_ref(node, *cands[0])

    def crossreference_title_ref(self, node, name, desc_type):
        nodetext = node.children[0].astext()
        reftype = DESCTYPE_TO_REFTYPE.get(desc_type, None)
        if reftype is None:
            return node

        newnode = pending_xref(nodetext, reftype=reftype, reftarget=name, modname=None, classname=None)
        node.replace_self(newnode)
        newnode += literal(nodetext, nodetext, classes=['xref'])

        # Yay, we found a new ref!
        self.new_pending_refs = True

    def depart_document(self, node):
        if not self.new_pending_refs:
            return

        # Re-resolve new pending references.
        builder = self.app.builder
        env = builder.env
        env.resolve_references(node, self.docname, builder)

    def unknown_visit(self, node):
        pass

    def unknown_departure(self, node):
        pass


def resolve_default_interpreted_role(app, doctree, docname):
    doctree.walkabout(DefaultInterpreter(app, doctree, docname))


def setup(app):
    app.connect('doctree-resolved', resolve_default_interpreted_role)
