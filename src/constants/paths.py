"""File system paths for VIIRS SCAGDRFS processing."""

from pathlib import Path
import os

# ── Project root ───────────────────────────────────────────────────────────────
# src/constants/paths.py → src/constants → src → <topdir>
TOPDIR = Path(__file__).resolve().parent.parent.parent

# ── PetaLibrary ────────────────────────────────────────────────────────────────
PETALIB_DIR = Path("/pl/active/daac-production")
PETALIB_STAGING_DIR = Path(f"{PETALIB_DIR}/scagdrfs/staging")
WATER_MASK_DIR = PETALIB_DIR / "post_process_watermasks"
DRFS_COMPONENT_DIR = PETALIB_DIR / "jpl_DRFS_Components"

V0_DIR = Path("/disks/sidads_ftp/pub/DATASETS/MODSCGDRF_NRT_v1.1")


# ── Product NRT dirs ───────────────────────────────────────────────────────────
def get_nrt_dir(product: str) -> Path:
    """Return the NRT input directory for *product*.

    Follows the standard layout: PETALIB_DIR/<product>/NRT.
    Override for a specific product by setting <PRODUCT>_NRT_DIR in the environment.
    """
    env_var = f"{product.upper()}_NRT_DIR"
    return Path(os.getenv(env_var, str(PETALIB_DIR / product / "NRT")))


# ── Scratch ────────────────────────────────────────────────────────────────────
WORK_DIR = Path(f"/scratch/alpine/{os.getenv('USER')}/scagdrfs/working")

# ── Constants ────────────────────────────────────────────────────────────────────
CONSTANTS_DIR = Path(os.getenv("CONSTANTS_DIR", TOPDIR / "src" / "constants"))

# ── Create scratch dirs on import ─────────────────────────────────────────────
for _dir in (WORK_DIR, PETALIB_STAGING_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# SSH/Transfer configuration
V0_USERNAME = os.getenv("V0_USERNAME", os.getenv("USER"))
V0_SSH_KEY = Path(os.getenv("V0_SSH_KEY", f"/home/{os.getenv('USER')}/.ssh/id_ecdsa"))
