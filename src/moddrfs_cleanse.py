"""Routines to "cleanse" the DRFS output

This is adapted from moddrfs_cleanse.pro (IDL)

IDL API:
   pro moddrfs_cleanse,prefix=prefix,ns=ns,nl=nl,mod09ga=mod09ga, threshold=threshold

IDL routine docstring:
     Input
         prefix    = prefix for all of the MODSCAG output filenames
         ns    = number of samples
         nl    = number of lines
         mod09ga = MOD09GA hdf file associated with the modscag outputs

     Output
         write new copies of the MODDRFS files with 'cleanse' added to
        the filename

Example template usage:
  Input filename template:   prefix + '.forcing.dat'
  Output filename template:  prefix + '.forcing.cleanse.dat'
"""

# TODO: This could be refactored if necessary, but would be best done in conjuction
#       with refactoring SCAG data variables which are likely to be "cleanse"d similarly.

import numpy as np


VAR_LIMITS = {
    'deltavis': {
        'min': np.float32(0.0),
        'max': np.float32(100.0),
    },
    'drfs.grnsz': {
        'min': np.float32(0.0),
        'max': np.float32(1100.0),
    },
    'forcing': {
        'min': np.float32(0.0),
        'max': np.float32(400.0),
        'error_val': np.float32(32.0),
    },
}
DRFS_BIP_MISSINGVAL = -2866


def moddrfs_cleanse(prefix, ns, nl, nbands=7):
    """Implement IDL routine moddrfs_cleanse()
    Some differences from IDL routine:
        BIP array is read from drfs_bip file instead of re-computed
        default threshold is not used
        nbands is set to kward in case this changes in future

    TODO: We may want to split up this function into several smaller functions?
    """

    # Set the input, output file names for each DRFS variable, and read in data
    drfs_vars = ('drfs.grnsz', 'forcing', 'deltavis')
    input_fns = {}
    output_fns = {}
    dat_arrays = {}
    for drfs_var in drfs_vars:
        input_fns[drfs_var] = prefix + '.' + drfs_var + '.dat'
        output_fns[drfs_var] = prefix + '.' + drfs_var + '.cleanse.dat'
        dat_arrays[drfs_var] = np.fromfile(input_fns[drfs_var], dtype=np.float32).reshape(nl, ns)

    # Compute where input is missing from drfs.bip file
    # NOTE: Here, we use the DRFS BIP file instead of re-calculating the BIP arrays
    bip_fn = prefix + '.drfs.bip'
    bip = np.fromfile(bip_fn, dtype=np.int16).reshape(nl, ns, nbands)
    is_bip_missing = bip == DRFS_BIP_MISSINGVAL
    is_bip_mask = np.sum(is_bip_missing.astype(np.uint8), axis=2) > 0

    # For drfs.grnsz: set missing to NaN, <min to 0; >max to max
    drfs_var = 'drfs.grnsz'
    data = dat_arrays[drfs_var]
    min_val = VAR_LIMITS[drfs_var]['min']
    max_val = VAR_LIMITS[drfs_var]['max']
    dat_arrays[drfs_var][data < min_val] = 0.0
    dat_arrays[drfs_var][data > max_val] = max_val
    dat_arrays[drfs_var][is_bip_mask] = np.nan

    # For forcing: set missing to NaN, <errval to NaN, errval to thres to 0, max to max+err to max,
    # >max_err to NaN <thresh to 0;
    drfs_var = 'forcing'
    data = dat_arrays[drfs_var]
    min_val = VAR_LIMITS[drfs_var]['min']
    max_val = VAR_LIMITS[drfs_var]['max']
    err_val = VAR_LIMITS[drfs_var]['error_val']
    dat_arrays[drfs_var][data < (min_val - err_val)] = np.nan
    dat_arrays[drfs_var][(data >= (min_val - err_val)) & (data < min_val)] = 0.0
    dat_arrays[drfs_var][(data > max_val) & (data <= (max_val + err_val))] = max_val
    dat_arrays[drfs_var][data >= (max_val + err_val)] = np.nan
    dat_arrays[drfs_var][is_bip_mask] = np.nan

    # For deltavis: set missing to NaN, <min to NaN; >max to NaNax
    drfs_var = 'deltavis'
    data = dat_arrays[drfs_var]
    min_val = VAR_LIMITS[drfs_var]['min']
    max_val = VAR_LIMITS[drfs_var]['max']
    dat_arrays[drfs_var][data < min_val] = np.nan
    dat_arrays[drfs_var][data > max_val] = np.nan
    dat_arrays[drfs_var][is_bip_mask] = np.nan

    # Write the output files
    for drfs_var in drfs_vars:
        output_fn = output_fns[drfs_var]
        dat_arrays[drfs_var].tofile(output_fn)
        print(f'  Wrote: {output_fn}')


if __name__ == '__main__':
    import sys

    prefix = sys.argv[1]

    moddrfs_cleanse(
        prefix,
        2400,
        2400,
    )
