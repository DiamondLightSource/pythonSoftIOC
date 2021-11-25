Use soft records in an IOC
==========================

It is possible to use records with soft device support mixed with pythonSoftIOC
records (with Python device support). This allows use of ``calc``, ``fanout``
and other EPICS database soft records.

.. literalinclude:: ../examples/example_records_calculate.py

The ``VAL1`` record is created in the usual pythonSoftIOC way, with Python
device support. You can :meth:`~softioc.device.ProcessDeviceSupportOut.set` it,
and `on_update` will be called when you ``caput`` it.

The ``VAL2`` record is created using the lower level
:attr:`softioc.builder.records` object. You can `dbpf` it, and no Python will
be called when you ``caput`` to it.

Note that the Device Name is shared between both kinds of records - both will
have the same prefix.

We construct the ``calc`` record again using :attr:`softioc.builder.records`.
This record will calculate ``A*B``:

- ``A`` is provided by the record pointed at by ``INPA``, which is
  ``py_record``, and the `CP` link causes it to be monitored, processing
  ``calc`` each time it updates.

- ``B`` is initially set to 1. When ``soft_record`` processes, it sends its
  value to ``calc.B``, and the `PP` link causes it to process.

.. note::

    You could also use ``calc(SCAN="1 second", ...)`` instead of the `PP` and
    `CP` links, which would fetch the value periodically rather than just on
    change.

The output of this IOC can be examined by running this IOC in one terminal, and
then modifying and running the example scripts found in `read-data-from-ioc`.
Try setting the value of either ``VAL1`` or ``VAL2`` and observe the effect on
the ``CALC`` output.
