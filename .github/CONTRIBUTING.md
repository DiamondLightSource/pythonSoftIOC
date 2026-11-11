# Contribute to the project

Contributions and issues are most welcome! All issues and pull requests are
handled through [GitHub](https://github.com/DiamondLightSource/pythonSoftIOC/issues). Also, please check for any existing issues before
filing a new one. If you have a great idea but it involves big changes, please
file a ticket before making a pull request! We want to make sure you don't spend
your time coding something that might not fit the scope of the project.

## Issue or Discussion?

Github also offers [discussions](https://github.com/DiamondLightSource/pythonSoftIOC/discussions) as a place to ask questions and share ideas. If
your issue is open ended and it is not obvious when it can be "closed", please
raise it as a discussion instead.

## Developer Information

It is recommended that developers use a [vscode devcontainer](https://code.visualstudio.com/docs/devcontainers/containers). This repository contains configuration to set up a containerized development environment that suits its own needs.

This project was created using the [Diamond Light Source Copier Template](https://github.com/DiamondLightSource/python-copier-template) for Python projects.

For more information on common tasks like setting up a developer environment, running the tests, and setting a pre-commit hook, see the template's [How-to guides](https://diamondlightsource.github.io/python-copier-template/5.5.0/how-to.html).

## Running the tests

The iocStats sources are a git submodule that is needed to build the
extension, so clone with `--recurse-submodules`. To get the source code and
run the unit tests, run:

```
git clone --recurse-submodules https://github.com/DiamondLightSource/pythonSoftIOC.git
cd pythonSoftIOC
uv sync
uv run tox -e tests
```

`uv sync` builds the extension and installs it, with the `dev` dependency
group, into a virtual environment. `uv run tox -p` runs the tests, lint, type
checking and docs build in parallel.

## Updating Dependencies

pythonSoftIOC has a variety of types of dependencies, from Python modules to
C files and built libraries. If it is necessary to update any of them, the
safest way to do that is:

```
# Ensure all changes are committed/saved/backed up
git clean -fdX
# Update dependencies in pyproject.toml / setup.py
uv lock --upgrade
uv sync
```

### The epicscorelibs build pin

The extension is built against epicscorelibs, and the epicscorelibs
dependency of the built package is pinned to the ABI of the version it was
built against.

- Released wheels and sdists (built by cibuildwheel or pip) use the
  epicscorelibs floor in `[build-system] requires` in `pyproject.toml`, so they
  always build against the newest epicscorelibs. They need no edit.
- `uv.lock` and the development environment use the epicscorelibs version
  pinned by `build-constraint-dependencies` in the `[tool.uv]` section of
  `pyproject.toml`. That pin is the only one to change: edit it, then run
  `uv lock --upgrade-package epicscorelibs` and `uv sync`. Renovate does not
  bump it.

## Code Styling

The code in this repository conforms to standards set by the following tools:

- [ruff](https://docs.astral.sh/ruff/) for style checks
- [pyright](https://microsoft.github.io/pyright/) for type checks

These are run by `uv run tox -e pre-commit,type-checking` and also
automatically at check in. Please read the tool documentation for details
on how to fix the errors it reports.

## Documentation

Documentation is contained in the `docs` directory and extracted from
docstrings of the API.

Docs follow the underlining convention:

```
Headling 1 (page title)
=======================

Heading 2
---------

Heading 3
~~~~~~~~~
```

You can build the docs from the project directory by running:

```
uv run tox -e docs
firefox build/html/index.html
```

## Release Process

To make a new release, please follow this checklist:

- Choose a new PEP440 compliant release number
- Git tag the version
- Push to github and the actions will make a release on pypi
- Push to internal gitlab but do not release from there
- Run `dls-py3 download-one-dependency softioc <release>`
- Run `uv export --frozen --no-dev --all-extras --no-hashes --no-emit-project > /dls_sw/work/python3/RHEL7-x86_64/distributions/softioc-<release>.requirements.txt`
- Run `dls-release.py -a python3ext softioc <release>`

Release notes are generated in GitHub Releases from the titles of the merged
pull requests; edit them there to add anything else, such as breaking changes.
