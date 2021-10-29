Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased_
-----------

Nothing yet

3.2_ - 2021-08-31
-----------------

Changed:

- Repository changed from pythonIoc to pythonSoftIOC
- Executable name changed from pythonIoc to pythonSoftIOC

Added:

- `Allow waveform.set() to be called before iocInit <../../pull/22>`_
- `Allow AsyncioDispatcher to take existing event loop <../../pull/28>`_
- `Support alarm.*_ALARM in mbb{In,Out} <../../pull/34>`_

Fixed:

- `Bug if multiple projects use VersionGit <../../pull/31>`_
- `Error if mbb{In,Out} given more that 16 labels <../../pull/33>`_


3.1_ - 2021-07-07
-----------------

Added:

- `PVA support to the IOC <../../pull/17>`_


3.0_ - 2021-07-05
-----------------

Added:

- `More documentation <../../pull/14>`_

Fixed:

- `Mbbi/o specifying alarm values bug introduced in 3.0b2 <../../pull/15>`_


3.0b2_ - 2021-06-28
-------------------

Changed:

- `Restructured the docs <../../pull/10>`_

Removed:

- Option of specifying scalar value for mbbi and mbbo records


3.0b1_ - 2021-06-28
-------------------

`Port to being a Python package <../../pull/5>`_

Changed:

- Removed ability to build as an EPICS module
- Restructure C code as Python extension
- Make devIocStats a submodule
- Now has a hard dependency on epicscorelibs

Added:

- asyncio support


2-16_ - 2019-12-10
------------------

Last release as an EPICS module rather than a Python package


.. _Unreleased: https://github.com/dls-controls/pythonIoc/compare/3.2...HEAD
.. _3.2: https://github.com/dls-controls/pythonIoc/compare/3.1...3.2
.. _3.1: https://github.com/dls-controls/pythonIoc/compare/3.0...3.1
.. _3.0: https://github.com/dls-controls/pythonIoc/compare/3.0b2...3.0
.. _3.0b2: https://github.com/dls-controls/pythonIoc/compare/3.0b1...3.0b2
.. _3.0b1: https://github.com/dls-controls/pythonIoc/compare/2-16...3.0b1
.. _2-16: https://github.com/dls-controls/pythonIoc/releases/tag/2-16
