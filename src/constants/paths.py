"""File system paths for VIIRS SCAGDRFS processing."""

from pathlib import Path
import os

# Get from environment
TOPDIR = Path(os.getenv("TOPDIR", Path(__file__).parent.parent.parent))
PETALIB_DIR = Path(os.getenv("PETALIB_DIR", "/pl/active/daac-production"))
PETALIB_STAGING_DIR = Path(
    os.getenv("PETALIB_STAGING_DIR", f"{PETALIB_DIR}/scagdrfs/staging")
)

V0_DIR = Path(os.getenv("V0_DIR", "/disks/sidads_ftp/pub/DATASETS/MODSCGDRF_NRT_v1.1"))
VJ109GA_NRT_DIR = Path(os.getenv("VJ109GA_NRT_DIR", f"{PETALIB_DIR}/VJ109GA/NRT"))
VNP09GA_NRT_DIR = Path(os.getenv("VNP09GA_NRT_DIR", f"{PETALIB_DIR}/VJNP09GA/NRT"))
MOD09GA_NRT_DIR = Path(os.getenv("MOD09GA_NRT_DIR", f"{PETALIB_DIR}/MOD09GA/NRT"))
VJ109GA_DIR = Path(os.getenv("VJ109GA_NRT_DIR", f"{PETALIB_DIR}/VJ109GA"))

WORK_DIR = Path(
    os.getenv("WORK_DIR", f"/scratch/alpine/{os.getenv('USER')}/viirs_scagdrfs/working")
)
CONSTANTS_DIR = Path(os.getenv("CONSTANTS_DIR", TOPDIR / "src" / "constants"))

# SSH/Transfer configuration
V0_USERNAME = os.getenv("V0_USERNAME", os.getenv("USER"))
V0_SSH_KEY = Path(os.getenv("V0_SSH_KEY", f"/home/{os.getenv('USER')}/.ssh/id_ecdsa"))
