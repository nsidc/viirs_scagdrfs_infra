/*
 * scag_limits.h - General limits used by scag programs
 *
 * 14-Jul-2021 M. J. Brodzik brodzik@nsidc.org 303-492-8263
 * Copyright (C) 2021 Regents of the University of Colorado
 */
#ifndef scag_limits_H
#define scag_limits_H

/* System headers here */

/* Scag headers here */

/* Scag-specific limits */
#define LIBHDRSIZE 256
#define SPECSIZE 560
#define BECKSIZE 1076
#define LIBSIZE 1120
#define NSPECBAND 252
#define SPECGAIN 2
#define ORIGIN 0
#define NAMELENGTH 13
#define MAXFILES 400
#define MAXSPEC 1000
#define SPECHDR 24
#define PERSPHDRSIZE 486
#define GAIN12BIT 4095
#define GAIN16BIT 65535
#define MAXREF 50
#define MAXLIST 400
#define MAXPATH 80
#define MAXBUF 100
#define MAXNAME 11
#define MAXSTRING 2560

#define MAXSAMPLES 9500
#define MAXLINES 9500

/* FIXME: why are there 2EMS, 3EMS and a general one? */
#define MAX2EMS 10
#define MAX3EMS 50
#define MAXEMS 10

#endif // scag_limits_H
