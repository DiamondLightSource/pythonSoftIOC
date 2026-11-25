Changelog
=========

This file is frozen at 4.7.2. Releases after 4.7.2 are documented in
`GitHub Releases <https://github.com/DiamondLightSource/pythonSoftIOC/releases>`_,
with release notes generated from the titles of the merged pull requests.

The entries below follow the format of `Keep a Changelog
<https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to `Semantic
Versioning <https://semver.org/spec/v2.0.0.html>`_.

4.7.2_ - 2026-09-11
-------------------

- `Add Python3.14 non-free-threading builds <https://github.com/DiamondLightSource/pythonSoftIOC/pull/212>`_

4.7.1_ - 2026-07-23
-------------------

Fixed:

- `Correctly set alarms during blocking processing <https://github.com/DiamondLightSource/pythonSoftIOC/pull/209>`_
- `Fix infinite loop when setting record's own value from on_update callback <https://github.com/DiamondLightSource/pythonSoftIOC/pull/202>`_

4.7.0_ - 2026-01-14
-------------------

Added:

- `Add support to change the callback buffer limit <https://github.com/DiamondLightSource/pythonSoftIOC/pull/194>`_

Fixed:

- `Update and fix iocStats <https://github.com/DiamondLightSource/pythonSoftIOC/pull/199>`_

4.6.1_ - 2025-04-22
-------------------

Fixed:

- `Fix releasing wheels for all platforms <https://github.com/DiamondLightSource/pythonSoftIOC/pull/189>`_

4.6.0_ - 2025-04-01
-------------------

Added:

- `Add autosave support to all records and record fields <https://github.com/DiamondLightSource/pythonSoftIOC/pull/163>`_
- `Add int64In/Out record support <https://github.com/DiamondLightSource/pythonSoftIOC/pull/161>`_
- `Enable setting alarm status of Out records <https://github.com/DiamondLightSource/pythonSoftIOC/pull/157>`_
- `Adding the non_interactive_ioc function <https://github.com/DiamondLightSource/pythonSoftIOC/pull/156>`_
- `Allow starting IOC without PVA <https://github.com/DiamondLightSource/pythonSoftIOC/pull/186>`_

Removed:

- `Remove python3.6 support <https://github.com/DiamondLightSource/pythonSoftIOC/pull/138>`_

Changed:

- `AsyncioDispatcher cleanup tasks atexit <https://github.com/DiamondLightSource/pythonSoftIOC/pull/138>`_
- `Ensure returned numpy arrays are not writeable <https://github.com/DiamondLightSource/pythonSoftIOC/pull/164>`_
- `Ensure records do not get stuck in processing state <https://github.com/DiamondLightSource/pythonSoftIOC/pull/175>`_
- `Remove __super attribute <https://github.com/DiamondLightSource/pythonSoftIOC/pull/187>`_

Fixed:

- `Fix conversion of ctypes pointers passed to C extension <https://github.com/DiamondLightSource/pythonSoftIOC/pull/154>`_

4.5.0_ - 2023-12-04
-------------------

Changed:

- `Add get_field and set_field methods to records <https://github.com/DiamondLightSource/pythonSoftIOC/pull/140>`_

Fixed:

- `Fix recursive set bug <https://github.com/DiamondLightSource/pythonSoftIOC/pull/141>`_

4.4.0_ - 2023-07-06
-------------------

Changed:

- `Improve string representation of RecordWrapper instances <https://github.com/DiamondLightSource/pythonSoftIOC/pull/130>`_
- `Use pvxslibs as PV Acess provider for IOC <https://github.com/DiamondLightSource/pythonSoftIOC/pull/132>`_

Fixed:

- `Fix devIocStats by including posix headers <https://github.com/DiamondLightSource/pythonSoftIOC/pull/134>`_

4.3.0_ - 2023-04-04
-------------------

Added:

- `Add Channel Access Report functions <https://github.com/DiamondLightSource/pythonSoftIOC/pull/115>`_
- Add ``WaveformIn`` to default exports from ``softioc.builder``

Fixed:

- `Allow arrays of strings to be used with Waveforms <https://github.com/DiamondLightSource/pythonSoftIOC/pull/102>`_
- `Fix DeprecationWarning from numpy when using "+" <https://github.com/DiamondLightSource/pythonSoftIOC/pull/123>`_

4.2.0_ - 2022-11-08
-------------------

Changed:

- Updated epicscorelibs to latest version, 7.0.7.99.0.0

Added:

- `Allow "status" and "severity" on In record init <https://github.com/DiamondLightSource/pythonSoftIOC/pull/111>`_
- `Allow users to reset the list of created records <https://github.com/DiamondLightSource/pythonSoftIOC/pull/114>`_

4.1.0_ - 2022-08-05
-------------------

Added:

- `Caput with callback <https://github.com/DiamondLightSource/pythonSoftIOC/pull/98>`_

Fixed:

- `Update asyncio example to use dispatcher for custom function <https://github.com/DiamondLightSource/pythonSoftIOC/pull/94>`_
- `Passing a custom asyncio event loop into the AsyncioDispatcher causes methods to never run <https://github.com/DiamondLightSource/pythonSoftIOC/pull/96>`_

4.0.2_ - 2022-06-06
-------------------

Changed:

- `Improve handling of range settings for scalar records <https://github.com/DiamondLightSource/pythonSoftIOC/pull/82>`_

Added:

- `Add Python 3.10 support <https://github.com/DiamondLightSource/pythonSoftIOC/pull/85>`_

Fixed:

- `Installing from sdist now works on Windows <https://github.com/DiamondLightSource/pythonSoftIOC/pull/86>`_


4.0.1_ - 2022-02-14
-------------------

Removed:

- `Remove python2 support <https://github.com/DiamondLightSource/pythonSoftIOC/pull/64>`_

Changed:

- `Default DISP to TRUE for all In records <https://github.com/DiamondLightSource/pythonSoftIOC/pull/74>`_
- `Overhaul record value setting/getting <https://github.com/DiamondLightSource/pythonSoftIOC/pull/60>`_

Added:

- New longStringIn/longStringOut record types

Fixed:

- `Zero length waveforms now warn of invalid length <https://github.com/DiamondLightSource/pythonSoftIOC/pull/55>`_
- `Out records without explicit initial value are now correctly validated <https://github.com/DiamondLightSource/pythonSoftIOC/pull/43>`_
- `stringOut record values can now be correctly set in all cases <https://github.com/DiamondLightSource/pythonSoftIOC/pull/40>`_
- `Waveforms will correctly use NELM keyword during initialization <https://github.com/DiamondLightSource/pythonSoftIOC/pull/37>`_


3.2.1_ - 2021-11-25
-------------------

Changed:

- `Allow installation for python 3.6 <https://github.com/DiamondLightSource/pythonSoftIOC/pull/51>`_

Added:

- Provide logging for exceptions raised in callbacks

Fixed:

- `Fixup atexit handling <https://github.com/DiamondLightSource/pythonSoftIOC/pull/35>`_
- `Fix main in Python2 <https://github.com/DiamondLightSource/pythonSoftIOC/pull/63>`_

3.2_ - 2021-08-31
-----------------

Changed:

- Repository changed from pythonIoc to pythonSoftIOC
- Executable name changed from pythonIoc to pythonSoftIOC

Added:

- `Allow waveform.set() to be called before iocInit <https://github.com/DiamondLightSource/pythonSoftIOC/pull/22>`_
- `Allow AsyncioDispatcher to take existing event loop <https://github.com/DiamondLightSource/pythonSoftIOC/pull/28>`_
- `Support alarm.*_ALARM in mbb{In,Out} <https://github.com/DiamondLightSource/pythonSoftIOC/pull/34>`_

Fixed:

- `Bug if multiple projects use VersionGit <https://github.com/DiamondLightSource/pythonSoftIOC/pull/31>`_
- `Error if mbb{In,Out} given more that 16 labels <https://github.com/DiamondLightSource/pythonSoftIOC/pull/33>`_


3.1_ - 2021-07-07
-----------------

Added:

- `PVA support to the IOC <https://github.com/DiamondLightSource/pythonSoftIOC/pull/17>`_


3.0_ - 2021-07-05
-----------------

Added:

- `More documentation <https://github.com/DiamondLightSource/pythonSoftIOC/pull/14>`_

Fixed:

- `Mbbi/o specifying alarm values bug introduced in 3.0b2 <https://github.com/DiamondLightSource/pythonSoftIOC/pull/15>`_


3.0b2_ - 2021-06-28
-------------------

Changed:

- `Restructured the docs <https://github.com/DiamondLightSource/pythonSoftIOC/pull/10>`_

Removed:

- Option of specifying scalar value for mbbi and mbbo records


3.0b1_ - 2021-06-28
-------------------

`Port to being a Python package <https://github.com/DiamondLightSource/pythonSoftIOC/pull/5>`_

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

.. _4.7.2:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.7.1...4.7.2
.. _4.7.1:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.7.0...4.7.1
.. _4.7.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.6.1...4.7.0
.. _4.6.1:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.6.0...4.6.1
.. _4.6.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.5.0...4.6.0
.. _4.5.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.4.0...4.5.0
.. _4.4.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.3.0...4.4.0
.. _4.3.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.2.0...4.3.0
.. _4.2.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.1.0...4.2.0
.. _4.1.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.0.2...4.1.0
.. _4.0.2:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/4.0.1...4.0.2
.. _4.0.1:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/3.2.1...4.0.1
.. _3.2.1:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/3.2...3.2.1
.. _3.2:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/3.1...3.2
.. _3.1:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/3.0...3.1
.. _3.0:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/3.0b2...3.0
.. _3.0b2:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/3.0b1...3.0b2
.. _3.0b1:
    https://github.com/DiamondLightSource/pythonSoftIOC/compare/2-16...3.0b1
.. _2-16:
    https://github.com/DiamondLightSource/pythonSoftIOC/releases/tag/2-16
