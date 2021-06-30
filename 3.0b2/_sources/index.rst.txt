.. include:: ../README.rst
    :end-before: when included in index.rst

How the documentation is structured
-----------------------------------

Documentation is split into four categories, accessible from links below or in
the side-bar. Use the links below or in the side-bar.

.. rst-class:: columns

Tutorials
~~~~~~~~~

Tutorials for installation, library and commandline usage. New users start here.

.. rst-class:: columns

How-to Guides
~~~~~~~~~~~~~

Practical step-by-step guides for the more experienced user.

.. rst-class:: columns

Explanations
~~~~~~~~~~~~

Explanation of how the library works and why it works that way.

.. rst-class:: columns

Reference
~~~~~~~~~

Technical reference material, for classes, methods, APIs, commands, and contributing to the project.

.. rst-class:: endcolumns

About the documentation
~~~~~~~~~~~~~~~~~~~~~~~

`Why is the documentation structured this way? <https://documentation.divio.com>`_

Table Of Contents
-----------------

.. toctree::
    :caption: Tutorials
    :name: tutorials
    :maxdepth: 1

    tutorials/installation
    tutorials/creating-an-ioc

.. toctree::
    :caption: How-to Guides
    :name: how-to
    :maxdepth: 1

    how-to/use-asyncio-in-an-ioc

.. toctree::
    :caption: Explanations
    :name: explanations
    :maxdepth: 1

    explanations/why-use-pythonIoc

.. rst-class:: no-margin-after-ul

.. toctree::
    :caption: Reference
    :name: reference
    :maxdepth: 1

    reference/api
    reference/contributing

* :ref:`genindex`
