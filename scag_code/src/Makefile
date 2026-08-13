#========================================================================
# Recursive make file for scag production system
#
# 2019-04-19 M. J. Brodzik 303-492-8263 brodzik@nsidc.org
# National Snow & Ice Data Center, University of Colorado, Boulder
# Copyright (C) 2019 Regents of University of Colorado
#========================================================================

# https://stackoverflow.com/a/10858332/238882
check_defined = \
    $(strip $(foreach 1,$1, \
        $(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
    $(if $(value $1),, \
      $(error Undefined $1$(if $2, ($2))))

$(call check_defined, SCAG_HOME, SCAG base folder)
$(call check_defined, SCAG_COMPILER, SCAG compiler)

#------------------------------------------------------------------------
# configuration section
#
# for compiling, installing and distributing you should be able
# to change these variables here and nowhere else and it should work
#
# PMESDR_TOPDIR should be the location you check the git repo out at
TOPDIR = $(SCAG_HOME)
INCDIR = $(TOPDIR)/src/include
LIBDIR = $(TOPDIR)/src/lib
BINDIR = $(TOPDIR)/bin

#
#	commands
#
#SHELL = /bin/sh
#RDIST = rdist

#
# C compiler options, debug or optimization settings
# These values will override any values in the subdirs
#
# For interactive debugging:
# -g - turns on debugging
# -debug all ??
# -O0 - turns off all optimizations
#       for icc, -O2 is the default
# -DDEBUG sets DEBUG to 1 for conditional compilation
#
#CONFIG_CFLAGS = -DDEBUG -g -debug all -O0 -m64
CONFIG_CFLAGS = -m64

#
#	system libraries and include directories
#

#
# end configuration section
#------------------------------------------------------------------------

# SUBDIRS = scagUtils scag tmscagSAT scag_sort
SUBDIRS = scagUtils scag scag_sort

all install clean:
	for i in $(SUBDIRS); do			\
	  (echo $$i; cd $$i;			\
	  $(MAKE) $@             		\
	    'CONFIG_CFLAGS=$(CONFIG_CFLAGS)'	\
	    'TOPDIR=$(TOPDIR)'	\
	    'BINDIR=$(BINDIR)'	\
	    'INCDIR=$(TOPDIR)/src/include' \
	    'LIBDIR=$(TOPDIR)/src/lib' \
	  ) || exit 1; \
	done
