##########################################################################
# Copyright (c) 2003 The University of Chicago, as Operator of Argonne
#     National Laboratory.
# Copyright (c) 2003 The Regents of the University of California, as
#     Operator of Los Alamos National Laboratory.
# EPICS BASE Versions 3.13.7 and higher are distributed subject to the
# Software License Agreement found in the file LICENSE that is included
# with this distribution.
##########################################################################

TOP=..

include $(TOP)/configure/CONFIG

USR_INCLUDES += -I$(PYTHON_BASE)/include/$(PYTHON)

USR_CFLAGS += -std=gnu99 -Werror


PROD_IOC_DEFAULT = softIoc
PROD_IOC_vxWorks = -nil-

DBD += softIoc.dbd
softIoc_DBD += base.dbd

USR_CFLAGS += -DEPICS_BASE='"$(shell cd "$(EPICS_BASE)" && pwd)"'
# The following LDFLAGS are required so that dynamically loaded Python modules
# can see the symbols exported by the linked Python interpreter.
USR_LDFLAGS += -Xlinker -export-dynamic

softIoc_SRCS += softIoc_registerRecordDeviceDriver.cpp
softIoc_SRCS += softMain.c

# We need to link against the EPICS Base libraries and Python
softIoc_LIBS += $(EPICS_BASE_IOC_LIBS) PythonSupport $(PYTHON)
# The following libraries appear to be required for Python 2.5
softIoc_SYS_LIBS += util dl
softIoc_LDFLAGS += -Wl,--rpath=$($(PYTHON)_DIR)

# Location of the python libraries
$(PYTHON)_DIR = $(PYTHON_BASE)/lib/$(PYTHON)/config



# ----------------------------------------------------------------------
# Support library for python component, dynamically loaded to assist with
# access to record fields.


LIBRARY_IOC += PythonSupport

# The following are compiled and added to the support library
PythonSupport_SRCS += PythonSupport.c

PythonSupport_LIBS += $(EPICS_BASE_IOC_LIBS)


# include $(TOP)/configure/RULES_TOP
include $(TOP)/configure/RULES
