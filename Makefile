#Makefile at top of application tree
TOP = .
include $(TOP)/configure/CONFIG
DIRS += configure
DIRS += softIocApp
DIRS += python
include $(TOP)/configure/RULES_TOP


# Note that we use pythonIoc to build its own documentation so that it can
# succuessfully import the softioc library.
SPHINX_BUILD := $(shell readlink -f $$(which sphinx-build))

BUILD_DOCS ?= 1

install: pythonIoc
ifeq ($(BUILD_DOCS),1)
install: docs
endif

clean: clean-pythonIoc

# Commands for creating startup script with correct paths to EPICS.
define SED_EDIT_COMMANDS
s:@@EPICS_BASE@@:$(EPICS_BASE):; \
s:@@EPICS_HOST_ARCH@@:$(EPICS_HOST_ARCH):
endef

# Ensure we get the build time EPICS_BASE into the executable
pythonIoc: pythonIoc.in
	sed '$(SED_EDIT_COMMANDS)' $^ >$@
	chmod +x $@

clean-pythonIoc:
	rm -f pythonIoc

docs: pythonIoc
	./pythonIoc $(SPHINX_BUILD) -b html docs docs/html

clean-docs:
	rm -rf docs/html

.PHONY: clean-pythonIoc clean-docs docs
