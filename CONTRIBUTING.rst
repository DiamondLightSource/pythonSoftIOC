Contributing
============

Contributions and issues are most welcome! All issues and pull requests are
handled through github on the `dls_controls repository`_. Also, please check for
any existing issues before filing a new one. If you have a great idea but it
involves big changes, please file a ticket before making a pull request! We
want to make sure you don't spend your time coding something that might not fit
the scope of the project.

.. _dls_controls repository: https://github.com/dls-controls/pythonIoc/issues

Running the tests
-----------------

To get the source source code and run the unit tests, run::

    $ git clone git://github.com/dls-controls/pythonIoc.git
    $ cd pythonIoc
    $ git submodule init
    $ git submodule update
    $ pipenv install --dev
    $ pipenv run tests

While 100% code coverage does not make a library bug-free, it significantly
reduces the number of easily caught bugs! Please make sure coverage remains the
same or is improved by a pull request!

Code Styling
------------

The code in this repository conforms to standards set by the following tools:

- flake8_ for style checks

.. _flake8: http://flake8.pycqa.org/en/latest/

These tests will be run on code when running ``pipenv run tests`` and also
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

    $ pipenv run docs
    $ firefox build/html/index.html


Release Checklist
-----------------

Before a new release, please go through the following checklist:

- Choose a new PEP440 compliant release number
- Git tag the version with a message summarizing the changes
- Push to github and the actions will make a release on pypi
- Push to internal gitlab and do a dls-release.py of the tag
