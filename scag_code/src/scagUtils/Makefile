#========================================================================
# Makefile for shared scag utility functions
#
# 2019-04-23 M. J. Brodzik 303-492-8263 brodzik@nsidc.org
# National Snow & Ice Data Center, University of Colorado, Boulder
# Copyright (C) 2019 Regents of University of Colorado
#========================================================================

#------------------------------------------------------------------------
# configuration section
#
#	installation directories
#
# TOPDIR = $(SCAG_TOPDIR)
# INCDIR = $(TOPDIR)/include
# LIBDIR = $(TOPDIR)/lib
# BINDIR = $(TOPDIR)/bin
TESTDIR = $(TOPDIR)/test
#COMPAREDIR = $(SCAG_REGRESS_DIR)
#COMPARE_TOLERANCE = $(SCAG_COMPARE_TOLERANCE)

#
#	commands
#
AR = ar
INSTALL = cp -f -p
MKDIR = mkdir -p
RM = rm -fr

#
# debug or optimization settings
# these may be things that are machine-specific
# note that if these are passed in by uberMakefile,
# the uberMakefile settings will override anything here
#
# CC = $(SCAG_COMPILER)
# ifeq ($(LOCALE),RCicc)
#    CONFIG_CFLAGS = -m64
# endif
# ifeq ($(LOCALE),RCgcc)
#    CONFIG_CFLAGS = 
# endif
# ifeq ($(LOCALE),UCSB)
#    CONFIG_CFLAGS = 
# endif

#$(info Build location: $(LOCALE))

#
#	system libraries
#
SYSLIBS = -lm

#
# end configuration section
#------------------------------------------------------------------------
LIBS = $(SYSLIBS)
# -Wall : enables all warnings and diagnostics
# -g -debug all -O0 : turns on debugging symbols
#CFLAGS = -g -debug all -O0 -I$(INCDIR) $(CONFIG_CFLAGS) \
#	-Wall
CFLAGS = -I$(INCDIR) $(CONFIG_CFLAGS) -Wall

DEPEND_LIBS =

SRCS = utils.c fileops.c mgsmix.c shdnorm.c geochecks.c
OBJS = utils.o fileops.o mgsmix.o shdnorm.o geochecks.o
HDRS = utils.h spec.h scag_limits.h


all : libscagUtils.a $(LIBDIR)/libscagUtils.a

$(LIBDIR)/libscagUtils.a : libscagUtils.a

libscagUtils.a : $(OBJS) $(DEPEND_LIBS) $(HDRS)
	$(AR) $(ARFLAGS) $@ $(OBJS)
	$(MKDIR) $(LIBDIR) $(INCDIR)
	$(INSTALL) $@ $(LIBDIR)
	$(INSTALL) $(HDRS) $(INCDIR)

install :

clean :
	- $(RM) libscatUtils.a $(OBJS)

