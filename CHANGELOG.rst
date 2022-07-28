Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog
<https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to `Semantic
Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased_
-----------

Fixed:

- `Passing a custom asyncio event loop into the AsyncioDispatcher causes methods to never run <../../pull/96>`_

4.0.2_ - 2022-06-06
-------------------

Changed:

- `Improve handling of range settings for scalar records <../../pull/82>`_

Added:

- `Add Python 3.10 support <../../pull/85>`_

Fixed:

- `Installing from sdist now works on Windows <../../pull/86>`_


4.0.1_ - 2022-02-14
-------------------

Removed:

- `Remove python2 support <../../pull/64>`_

Changed:

- `Default DISP to TRUE for all In records <../../pull/74>`_
- `Overhaul record value setting/getting <../../pull/60>`_

Added:

- New longStringIn/longStringOut record types

Fixed:

- `Zero length waveforms now warn of invalid length <../../pull/55>`_
- `Out records without explicit initial value are now correctly validated <../../pull/43>`_
- `stringOut record values can now be correctly set in all cases <../../pull/40>`_
- `Waveforms will correctly use NELM keyword during initialization <../../pull/37>`_


3.2.1_ - 2021-11-25
-------------------

Changed:

- `Allow installation for python 3.6 <../../pull/51>`_

Added:

- Provide logging for exceptions raised in callbacks

Fixed:

- `Fixup atexit handling <../../pull/35>`_
- `Fix main in Python2 <../../pull/63>`_

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


.. _Unreleased: https://github.com/dls-controls/pythonIoc/compare/4.0.2...HEAD
.. _4.0.2: https://github.com/dls-controls/pythonIoc/compare/4.0.1...4.0.2
.. _4.0.1: https://github.com/dls-controls/pythonIoc/compare/3.2.1...4.0.1
.. _3.2.1: https://github.com/dls-controls/pythonIoc/compare/3.2...3.2.1
.. _3.2: https://github.com/dls-controls/pythonIoc/compare/3.1...3.2
.. _3.1: https://github.com/dls-controls/pythonIoc/compare/3.0...3.1
.. _3.0: https://github.com/dls-controls/pythonIoc/compare/3.0b2...3.0
.. _3.0b2: https://github.com/dls-controls/pythonIoc/compare/3.0b1...3.0b2
.. _3.0b1: https://github.com/dls-controls/pythonIoc/compare/2-16...3.0b1
.. _2-16: https://github.com/dls-controls/pythonIoc/releases/tag/2-16
