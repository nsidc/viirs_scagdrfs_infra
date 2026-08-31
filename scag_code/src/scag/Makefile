#========================================================================
# Makefile for scag
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
LIBS = -L$(LIBDIR) -lscagUtils $(SYSLIBS)

# -Wall - enables all warnings and diagnostics
# -g -debug all -O0 : turns on debugging symbols
#CFLAGS = -g -debug all -O0 -I$(INCDIR) $(CONFIG_CFLAGS) -Wall
CFLAGS = -I$(INCDIR) $(CONFIG_CFLAGS) -Wall

DEPEND_LIBS = $(LIBDIR)/libscagUtils.a

SRCS = scag.c
OBJS = scag.o
HDRS = $(INCDIR)/spec.h $(INCDIR)/utils.h $(INCDIR)/scag_limits.h
BIN = scag


all : $(BIN)

$(BIN) : $(OBJS) $(HDRS) $(DEPEND_LIBS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LIBS)

install :
	$(MKDIR) $(BINDIR)
	$(INSTALL) $(BIN) $(BINDIR)

clean :
	$(RM) $(BIN) $(OBJS) $(BINDIR)/$(BIN)

