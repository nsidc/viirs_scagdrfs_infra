"""Separate the slope and aspect into two different files"""

import numpy as np
import sys
import os

# Typical file name:
#  h09v05_500m_slope_aspect.bsq
ifn = sys.argv[1]
fn_slope = sys.argv[2]
fn_aspect = sys.argv[3]
assert fn_slope != ifn
assert fn_aspect != ifn

bfn = os.path.basename(ifn)
if '1km' in ifn:
    dim = 1200
else:
    print('assuming 500m...')
    dim = 2400

slopeaspect = np.fromfile(ifn, dtype=np.float32).reshape(2, dim, dim)

slope = slopeaspect[0, : , :]
aspect = slopeaspect[1, : , :]

#fn_slope = bfn.replace('slope_aspect', 'slope')
#fn_aspect = bfn.replace('slope_aspect', 'aspect')

#if fn_slope == ifn:
#    fn_slope = ifn.replace('.bsq', '_slope.bsq')
#assert fn_slope != ifn

#if fn_aspect == ifn:
#    fn_aspect = ifn.replace('.bsq', '_aspect.bsq')
#assert fn_aspect != ifn

slope.tofile(fn_slope)
aspect.tofile(fn_aspect)

print(f'  Wrote: {fn_slope}')
print(f'  Wrote: {fn_aspect}')
