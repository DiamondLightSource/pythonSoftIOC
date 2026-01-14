Building pythonSoftIOC with ``uv``
==================================

There are some issues when using the ``uv`` tool to build pythonSoftIOC, which
may happen if you try and use this package on an architecture or Python version
where we do not supply pre-built wheels.

If you see an ``ImportError`` that looks like this when running your application::

    src/techui_builder/builder.py:13: in <module>
        from softioc.builder import records
    /cache/venv-for/scratch/eyh46967/dev/temp/techui-builder/lib/python3.13/site-packages/softioc/__init__.py:14: in <module>
        from .imports import dbLoadDatabase, registerRecordDeviceDriver
    /cache/venv-for/scratch/eyh46967/dev/temp/techui-builder/lib/python3.13/site-packages/softioc/imports.py:10: in <module>
        from . import _extension
    E   ImportError: libdbCore.so.7.0.10.99.0: cannot open shared object file: No such file or directory


Then you need to add these lines to your ``pyproject.toml`` file::

    [tool.uv.extra-build-dependencies]
    softioc = [{ requirement = "epicscorelibs", match-runtime = true }]

This will tell ``uv`` to do additional dependency checking between build-time and
run-time environments, ensuring the same version of ``epicscorelibs`` is used
in both.

See discussion in `uv issue #17378 <https://github.com/astral-sh/uv/issues/17378>`_.
