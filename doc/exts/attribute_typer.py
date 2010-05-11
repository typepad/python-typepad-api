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

A Sphinx extension to rewrite attribute description units with their type information.

"""


from docutils.nodes import NodeVisitor, SparseNodeVisitor, Part, Inline, TextElement, title_reference
import re

from sphinx.addnodes import desc, desc_type, desc_signature, desc_addname


class desc_attrtype(Part, Inline, TextElement):

    @staticmethod
    def visit_html(html, node):
        html.body.append(' &rarr; ')

    @staticmethod
    def depart_html(html, node):
        pass


class attrtype_role(Part, Inline, TextElement):
    pass


class DefaultInterpreter(SparseNodeVisitor):

    def __init__(self, app, document, docname):
        SparseNodeVisitor.__init__(self, document)
        self.app = app
        self.docname = docname
        self.desc_scope = []

    def visit_desc(self, node):
        self.desc_scope.append(None)

    def depart_desc(self, node):
        attrtype_text = self.desc_scope.pop()
        if attrtype_text is not None:
            # make the insides of the attrtype a crossreferencible reference
            this_attrtype = desc_attrtype()
            this_attrtype.append(title_reference(attrtype_text, attrtype_text))
            # find the desc_signature
            this_signature = node.traverse(desc_signature)
            # add the attrtype to the desc_signature
            this_signature[0].append(this_attrtype)

    def depart_attrtype_role(self, node):
        self.desc_scope[-1] = node.children[0].astext()
        node.parent.remove(node)

    def depart_paragraph(self, node):
        # Clean up empty paragraphs.
        if not node.children:
            node.parent.remove(node)

    def unknown_visit(self, node):
        pass

    def unknown_departure(self, node):
        pass


def move_attribute_types(app, doctree, docname):
    doctree.walkabout(DefaultInterpreter(app, doctree, docname))


def setup(app):
    app.add_generic_role('attrtype', attrtype_role)
    app.add_node(desc_attrtype, html=(desc_attrtype.visit_html, desc_attrtype.depart_html))
    app.connect('doctree-resolved', move_attribute_types)
