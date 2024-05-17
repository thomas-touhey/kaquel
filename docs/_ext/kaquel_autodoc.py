#!/usr/bin/env python
# *****************************************************************************
# Copyright (C) 2024 Thomas Touhey <thomas@touhey.fr>
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software. You can use, modify
# and/or redistribute the software under the terms of the CeCILL-C license
# as circulated by CEA, CNRS and INRIA at the following
# URL: https://cecill.info
#
# As a counterpart to the access to the source code and rights to copy, modify
# and redistribute granted by the license, users are provided only with a
# limited warranty and the software's author, the holder of the economic
# rights, and the successive licensors have only limited liability.
#
# In this respect, the user's attention is drawn to the risks associated with
# loading, using, modifying and/or developing or reproducing the software by
# the user in light of its specific status of free software, that may mean
# that it is complicated to manipulate, and that also therefore means that it
# is reserved for developers and experienced professionals having in-depth
# computer knowledge. Users are therefore encouraged to load and test the
# software's suitability as regards their requirements in conditions enabling
# the security of their systems and/or data to be ensured and, more generally,
# to use and operate it in the same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.
# *****************************************************************************
"""Sphinx extensions for autodoc."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from sphinx.application import Sphinx


def remove_first_line_in_module_docstring(
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Any,
    lines: list[str],
) -> None:
    """Remove the first line (and empty line) of the docstring if is a module.

    See `autodoc-process-docstring`_ for more information regarding the
    signature.

    .. _autodoc-process-docstring:
        https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
        #event-autodoc-process-docstring
    """
    if what != "module" or not lines:
        return

    for i in range(1, len(lines)):
        if not lines[i]:
            lines[: i + 1] = []
            return

    lines[:] = []


def setup(app: Sphinx) -> None:
    """Set up the extension.

    :param app: The Sphinx application to set up the extension for.
    """
    app.connect(
        "autodoc-process-docstring",
        remove_first_line_in_module_docstring,
    )
