#Makefile at top of application tree
TOP = .
include $(TOP)/configure/CONFIG
DIRS += configure
DIRS += softIocApp
DIRS += python
include $(TOP)/configure/RULES_TOP
