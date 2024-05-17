"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

from __future__ import annotations

from pathlib import Path
import sys

from toml import load as load_toml


# Add the module path.
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent / "_ext"))
pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

with open(pyproject_path) as pyproject_file:
    version = load_toml(pyproject_file)["tool"]["poetry"]["version"]

project = "Kaquel"
copyright = "2024, Thomas Touhey"
author = "Thomas Touhey"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinxcontrib.mermaid",
    "kaquel_autodoc",
]

templates_path: list[str] = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = f"Kaquel {version}"
html_favicon = "_static/favicon.png"
html_logo = "_static/logo.png"
html_use_index = False
html_copy_source = False
html_show_sourcelink = False
html_domain_indices = False
html_css_files = ["custom.css"]

intersphinx_mapping: dict[str, tuple[str, None]] = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
}

todo_include_todos = True

mermaid_output_format = "raw"
mermaid_init_js = """
function isDarkMode() {
    const color = (
        getComputedStyle(document.body)
        .getPropertyValue("--color-code-foreground")
    );

    if (color == "#d0d0d0")
        return true;

    return false;
}

function initializeMermaid(isStart) {
    mermaid.initialize({
        startOnLoad: isStart,
        theme: isDarkMode() ? "dark" : "base",
        darkMode: isDarkMode(),
        securityLevel: "antiscript"
    });
}

const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (
            mutation.type != "attributes"
            || mutation.attributeName != "data-theme"
        )
            return

        const nodes = document.querySelectorAll(".mermaid");
        nodes.forEach(node => {
            /* Restore the original code before reprocessing. */
            node.innerHTML = node.getAttribute("data-original-code");

            /* Remove the attribute saying data is processed; it is not! */
            if (node.hasAttribute("data-processed"))
                node.removeAttribute("data-processed");
        });

        initializeMermaid(false);
        mermaid.run({nodes: nodes, querySelector: ".mermaid"});
    });
});

(function (window) {
    /* Store original code for diagrams into an attribute directly, since
       Mermaid actually completely replaces the content and removes the
       original code. */
    document.querySelectorAll(".mermaid").forEach(node => {
        node.setAttribute("data-original-code", node.innerHTML);
    })

    initializeMermaid(true);
    observer.observe(document.body, {attributes: true});
})(window);
"""

autodoc_typehints_format = "short"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "exclude-members": "model_config, model_fields, model_computed_fields",
}
autodoc_member_order = "bysource"
