Contributing
============

Contributions and issues are most welcome! All issues and pull requests are
handled through github on the `dls_controls repository`_. Also, please check for
any existing issues before filing a new one. If you have a great idea but it
involves big changes, please file a ticket before making a pull request! We
want to make sure you don't spend your time coding something that might not fit
the scope of the project.

.. _dls_controls repository:
    https://github.com/DiamondLightSource/pythonSoftIOC/issues

Running the tests
-----------------

To get the source source code and run the unit tests, run::

    $ git clone --recurse-submodules https://github.com/DiamondLightSource/pythonSoftIOC.git
    $ cd pythonSoftIOC
    $ uv sync
    $ uv run tox -e tests

``uv sync`` builds the extension and installs it, with the ``dev`` dependency
group, into a virtual environment. ``uv run tox -p`` runs the tests, lint, type
checking and docs build in parallel.

This project was created using the `python-copier-template`_; its
`how-to guides`_ describe common tasks such as setting up a developer
environment and installing the pre-commit hooks.

.. _python-copier-template:
    https://github.com/DiamondLightSource/python-copier-template
.. _how-to guides:
    https://diamondlightsource.github.io/python-copier-template/5.5.0/how-to.html

While 100% code coverage does not make a library bug-free, it significantly
reduces the number of easily caught bugs! Please make sure coverage remains the
same or is improved by a pull request!


Updating Dependencies
---------------------

pythonSoftIoc has a variety of types of dependencies, from Python module to
C files and built libraries. If it is necessary to update any of them, the
safest way to do that is::

    $ Ensure all changes are committed/saved/backed up
    $ git clean -fdX
    $ Update dependencies in pyproject.toml / setup.py
    $ uv lock --upgrade
    $ uv sync

Code Styling
------------

The code in this repository conforms to standards set by the following tools:

- ruff_ for style checks
- pyright_ for type checks

.. _ruff: https://docs.astral.sh/ruff/
.. _pyright: https://microsoft.github.io/pyright/

These are run by ``uv run tox -e pre-commit,type-checking`` and also
automatically at check in. Please read the tool documentation for details
on how to fix the errors it reports.

Documentation
-------------

Documentation is contained in the ``docs`` directory and extracted from
docstrings of the API.

Docs follow the underlining convention::

    Headling 1 (page title)
    =======================

    Heading 2
    ---------

    Heading 3
    ~~~~~~~~~


You can build the docs from the project directory by running::

    $ uv run tox -e docs
    $ firefox build/html/index.html


Release Process
---------------

To make a new release, please follow this checklist:

- Choose a new PEP440 compliant release number
- Add a release note in CHANGELOG.rst
- Git tag the version
- Push to github and the actions will make a release on pypi
- Push to internal gitlab but do not release from there
- Run ``dls-py3 download-one-dependency softioc <release>``
- Run ``dls-release.py -a python3ext softioc <release>``
