Use ``iocbuilder`` records in an IOC
======================================

It is possible to use ``iocbuilder`` records mixed with pythonSoftIOC records. 
This allows use of lower level EPICS constructs and syntax, if preferred.

.. literalinclude:: ../examples/example_records_calculate.py

The ``VAL1`` record is created in the usual pythonSoftIOC way. 

The ``VAL2`` record is created using the lower level :attr:`softioc.builder.records` object,
using EPICS syntax and notations, but it is conceptually the same as the record created
by pythonSoftIOC.
Note that the Device Name is shared between both kinds of records - both will have the same prefix.

We construct the ``calc`` record again using :attr:`softioc.builder.records`. This record will calculate 
the result of record A, the ``softioc`` record, multiplied by record B, the ``iocbuilder`` record. 
The ``SCAN`` parameter will cause this calculation to trigger once every second. 

.. note::
    There are many ways the ``calc`` record could be created and triggered. For example, it could use 
    forward links or fanouts in place of the ``SCAN`` to achieve the same result, but these are beyond 
    the scope of this tutorial.

The output of this IOC can be examined by running this IOC in one terminal, and then modifying 
and running the example scripts found in `read-data-from-ioc`. Try setting the value of either ``VAL1`` 
or ``VAL2`` and observe the effect on the ``CALC`` output.
