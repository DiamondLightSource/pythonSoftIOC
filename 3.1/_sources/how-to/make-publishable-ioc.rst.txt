Create a Publishable IOC
========================

As seen in `../tutorials/creating-an-ioc`, a single Python script can be an IOC.
It is also possible (and the most common situation) to have an entire Python module
comprising an IOC. This guide explains both, as well as how to publish an IOC within
the DLS environment.

Single File IOC
----------------
An IOC that is entirely contained within a single Python source file can be used as an 
IOC inside DLS simply by adding this shebang line::

    #!/dls_sw/prod/python3/RHEL7-x86_64/softioc/3.0b2/prefix/bin/pythonIoc


IOC entry point for a module
------------------------------
If your IOC is more complicated than one file, it is recommended to write a python 
module (including docs/tests/etc.). The Panda Blocks Client will be an example of
this.


Make an IOC publishable at DLS
------------------------------
To make the IOC publishable, a makefile is required:

``Makefile``
    This file is necessary in order to run ``dls-release.py``, and needs to have
    both ``install`` and ``clean`` targets, but doesn't need to actually do
    anything.  Thus the following content for this file is enough::

        install:
        clean:

