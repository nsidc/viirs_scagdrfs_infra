"""File system paths for VIIRS SCAGDRFS processing."""

from pathlib import Path
import os

# ── Project root ─────────────────────────────────────────────────────────────
# src/constants/paths.py → src/constants → src → <topdir>
TOPDIR = Path(__file__).resolve().parent.parent.parent

# ── Data directories ───────────────────────────────────────────────────────-─
PETALIB_DIR = Path("/pl/active/daac-production")
PETALIB_STAGING_DIR = Path(f"{PETALIB_DIR}/scagdrfs/staging")
# DRFS_COMPONENT_DIR = PETALIB_DIR / "viirsscgdrf_ancillary_v0"
DRFS_COMPONENT_DIR = PETALIB_DIR / "viirsscgdrf_ancillary_v1"
WATER_MASK_DIR = DRFS_COMPONENT_DIR / "waterpercentage"
V0_DIR = Path("/disks/sidads_ftp/pub/DATASETS/MODSCGDRF_NRT_v1.1")


# ── Product dirs ────────────────────────────────────────────────────────----─
def get_nrt_dir(product: str) -> Path:
    """Return the NRT input directory for *product*.

    Follows the standard layout: PETALIB_DIR/<product>/NRT.
    Override for a specific product by setting <PRODUCT>_NRT_DIR in the env.
    """
    product = product.upper()
    env_var = f"{product}_NRT_DIR"
    return Path(os.getenv(env_var, str(PETALIB_DIR / product / "NRT")))


def get_final_dir(product: str) -> Path:
    """Return the final (non-NRT) input directory for *product*.

    Follows the standard layout: PETALIB_DIR/<product>/FIN.
    Override by setting <PRODUCT>_DIR in the environment.
    """
    product = product.upper()
    env_var = f"{product}_DIR"
    return Path(os.getenv(env_var, str(PETALIB_DIR / product / "FIN")))


def get_slurm_scratch(product: str, day, tile) -> Path:
    """Node-local scratch dir for one product/day/tile.

    Only valid inside a Slurm job; the directory is deleted when the job ends.
    """
    scratch = os.getenv("SLURM_SCRATCH")
    if scratch is None:
        raise RuntimeError("SLURM_SCRATCH is not set — must run in Slurm job")
    return Path(scratch) / product.upper() / day.strftime("%Y.%m.%d") / tile


# ── Scratch ──────────────────────────────────────────────────────────────────
WORK_DIR = Path(f"/scratch/alpine/{os.getenv('USER')}/scagdrfs/working")
STAGE_DIR = Path(f"/scratch/alpine/{os.getenv('USER')}/scagdrfs/staging")

# ── Constants ────────────────────────────────────────────────────────────────
CONSTANTS_DIR = Path(os.getenv("CONSTANTS_DIR", TOPDIR / "src" / "constants"))

# ── Create scratch dirs on import ────────────────────────────────────────────
for _dir in (WORK_DIR, PETALIB_STAGING_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# SSH/Transfer configuration
V0_USERNAME = os.getenv("V0_USERNAME", os.getenv("USER"))
V0_SSH_KEY = Path(
    os.getenv("V0_SSH_KEY", f"/home/{os.getenv('USER')}/.ssh/id_ecdsa"))
