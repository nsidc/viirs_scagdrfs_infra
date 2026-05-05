"""Compare Python DRFS outputs against IDL golden reference."""

import numpy as np
from pathlib import Path

FLAG = -9999.99

golden_dir = Path("/pl/active/daac-production/drfs_regression/golden/h09v05")
working_dir = Path("/scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05")
stem = "MOD09GA.A2026068.h09v05.061.2026069014006.NRT"

fields = {
    "deltavis": ("deltavis.dat", "deltavis.dat"),
    "forcing": ("forcing.dat", "forcing.dat"),
    "grnsz": ("drfs.grnsz.dat", "drfs.grnsz.dat"),
}

for field, (golden_fname, python_fname) in fields.items():
    ref = np.fromfile(golden_dir / f"{stem}.{golden_fname}", dtype=np.float32).reshape(
        2400, 2400
    )
    out = np.fromfile(working_dir / f"{stem}.{python_fname}", dtype=np.float32).reshape(
        2400, 2400
    )

    valid_mask = ref > FLAG
    n_valid = np.sum(valid_mask)

    if n_valid == 0:
        print(f"{field}: no valid pixels in reference")
        continue

    diff = out[valid_mask] - ref[valid_mask]
    print(f"\n{field}:")
    print(f"  n_valid pixels in ref: {n_valid}")
    print(f"  n_valid pixels in out: {np.sum(out > FLAG)}")
    print(f"  mean diff:  {diff.mean():.6f}")
    print(f"  max abs diff: {np.abs(diff).max():.6f}")
    print(f"  pct within 0.01: {np.mean(np.abs(diff) < 0.01) * 100:.1f}%")
    print(f"  pct within 0.1:  {np.mean(np.abs(diff) < 0.1) * 100:.1f}%")


grnsz_ref = np.fromfile(
    golden_dir / f"{stem}.drfs.grnsz.dat", dtype=np.float32
).reshape(2400, 2400)
grnsz_out = np.fromfile(
    working_dir / f"{stem}.drfs.grnsz.dat", dtype=np.float32
).reshape(2400, 2400)
deltavis_ref = np.fromfile(
    golden_dir / f"{stem}.deltavis.dat", dtype=np.float32
).reshape(2400, 2400)
deltavis_out = np.fromfile(
    working_dir / f"{stem}.deltavis.dat", dtype=np.float32
).reshape(2400, 2400)

# Pixels valid in ref but flagged in output
ref_valid = grnsz_ref > FLAG
out_valid = grnsz_out > FLAG
missing = ref_valid & ~out_valid
extra = ~ref_valid & out_valid
print(f"grnsz missing pixels (valid in ref, flagged in out): {np.sum(missing)}")
print(f"grnsz extra pixels (flagged in ref, valid in out): {np.sum(extra)}")

# For pixels valid in both, how close are grnsz values?
both_valid = ref_valid & out_valid
diff = grnsz_out[both_valid] - grnsz_ref[both_valid]
print(f"\ngrnsz where both valid ({np.sum(both_valid)} pixels):")
print(f"  mean diff: {diff.mean():.4f}")
print(f"  max abs diff: {np.abs(diff).max():.4f}")
print(f"  pct within 0.01: {np.mean(np.abs(diff) < 0.01)*100:.1f}%")

# For deltavis, check pixels valid in both
ref_dv_valid = deltavis_ref > FLAG
out_dv_valid = deltavis_out > FLAG
both_dv = ref_dv_valid & out_dv_valid
print(f"\ndeltavis pixels valid in both: {np.sum(both_dv)}")
if np.sum(both_dv) > 0:
    diff_dv = deltavis_out[both_dv] - deltavis_ref[both_dv]
    print(f"  mean diff: {diff_dv.mean():.4f}")
    print(f"  max abs diff: {np.abs(diff_dv).max():.4f}")
    print(f"  pct within 0.01: {np.mean(np.abs(diff_dv) < 0.01)*100:.1f}%")
    print(f"  pct within 1.0:  {np.mean(np.abs(diff_dv) < 1.0)*100:.1f}%")
    # Sample a few pixels to compare
    sample_idx = np.where(both_dv)
    for k in range(5):
        i, j = sample_idx[0][k], sample_idx[1][k]
        print(
            f"  pixel ({i},{j}): ref={deltavis_ref[i,j]:.4f} out={deltavis_out[i,j]:.4f}"
        )
