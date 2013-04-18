#Makefile at top of application tree
TOP = .
include $(TOP)/configure/CONFIG
DIRS += configure
DIRS += softIocApp
DIRS += python
include $(TOP)/configure/RULES_TOP


install: pythonIoc

clean: clean-pythonIoc


# Ensure we get the build time EPICS_BASE into the executable
pythonIoc: pythonIoc.in
	sed 's:@@EPICS_BASE@@:$(EPICS_BASE):;s:@@EPICS_HOST_ARCH@@:$(EPICS_HOST_ARCH):' $^ >$@
	chmod +x $@

clean-pythonIoc:
	rm -f pythonIoc

.PHONY: clean-pythonIoc
