#!/usr/bin/env python

import os
import ast
import json
import glob
import numpy as np
import pandas as pd
import xarray as xr
import rioxarray as rxr
import h5py
import re

from pathlib import Path

from abc import ABC, abstractmethod
from argparse import ArgumentParser


MAX_INT16 = 2 ** 8 - 1

meta = pd.Series(
    dtype=np.float32,
    index=[
        "SOURCE_FILE",
        "SENSOR",
        "NLINES",
        "NSAMPLES",
        "NBANDS",
        "SUN_ZENITH",
        "PROJ_STRING",
        "ZONE_NUMBER",
        "ELLIPSOID",
        "DATUM",
        "GRID_CELL_SIZE_REFLECTIVE",
        "CORNER_UL_PROJECTION_X_PRODUCT",
        "CORNER_UL_PROJECTION_Y_PRODUCT",
        "CORNER_LR_PROJECTION_X_PRODUCT",
        "CORNER_LR_PROJECTION_Y_PRODUCT",
    ],
)


class Strategy(ABC):
    """Strategy design pattern

    Provide a uniform interface to different satellite files"""

    @abstractmethod
    def __init__(self, infile: str = "") -> None:
        pass

    @abstractmethod
    def load(self) -> np.ndarray:
        """Load the data from this product,

        Returns a 3D (x,y,band) numpy array"""
        pass

    @abstractmethod
    def SCAG_meta(self) -> None:
        """Load the SCAG-specific metadata from this product.

        Format as an xarray dataarray"""
        pass


class MOD09GA(Strategy):
    def __init__(self, infile: str = "") -> None:
        assert infile != ""
        self._infile = infile

    def load(self) -> np.ndarray:
        ds = xr.open_dataset(self._infile, engine="netcdf4")

        # MODIS bands are not numbered in order of increasing reflecance wavelength.
        # This sorts them in increasing wavelength order.
        # MOD09GA var name is like:
        #   sur_refl_b03_1  and is 'short' of size (2400,2400) with scale_factor 0.0001
        band_order = [3, 4, 1, 2, 5, 6, 7]
        band_names = ["sur_refl_b" + str(b).zfill(2) + "_1" for b in band_order]
        data = ds[band_names].to_array().data
        return data

    def SCAG_meta(self) -> pd.Series:
        ds = xr.open_dataset(self._infile, engine="netcdf4")

        am = self.parse_hdfeos_metadata(ds.attrs["ArchiveMetadata.0"])
        cm = self.parse_hdfeos_metadata(ds.attrs["CoreMetadata.0"])
        sm = self.parse_hdfeos_metadata(ds.attrs["StructMetadata.0"])

        meta["SOURCE_FILE"] = str(self._infile.resolve())
        meta["NBANDS"] = "7"
        meta["SENSOR"] = "MODIS"
        meta["NLINES"] = ds.dims["YDim:MODIS_Grid_500m_2D"]
        meta["NSAMPLES"] = ds.dims["XDim:MODIS_Grid_500m_2D"]

        meta["SUN_ZENITH"] = ds["SolarZenith_1"][  # Use center value from 1 km product
            int(ds["XDim:MODIS_Grid_1km_2D"].size / 2),
            int(ds["YDim:MODIS_Grid_1km_2D"].size / 2),
        ].data  # range is 0 to 18000 -> 0 to 180.

        meta["PROJ_STRING"] = "+proj=sinu +R=6371007.181 +nadgrids=@null +wktext"
        meta["ZONE_NUMBER"] = cm["INVENTORYMETADATA"]["ECSDATAGRANULE"][
            "LOCALGRANULEID"
        ]["VALUE"].split(".")[2]
        meta["ELLIPSOID"] = ast.literal_eval(
            sm["GridStructure"]["GRID_1"]["ProjParams"]
        )[0]
        meta["DATUM"] = "WGS84"
        meta["GRID_CELL_SIZE_REFLECTIVE"] = am["ARCHIVEDMETADATA"][
            "CHARACTERISTICBINSIZE500M"
        ]["VALUE"]
        meta["CORNER_UL_PROJECTION_X_PRODUCT"] = ast.literal_eval(
            sm["GridStructure"]["GRID_1"]["UpperLeftPointMtrs"]
        )[0]
        meta["CORNER_UL_PROJECTION_Y_PRODUCT"] = ast.literal_eval(
            sm["GridStructure"]["GRID_1"]["UpperLeftPointMtrs"]
        )[1]
        meta["CORNER_LR_PROJECTION_X_PRODUCT"] = ast.literal_eval(
            sm["GridStructure"]["GRID_1"]["LowerRightMtrs"]
        )[0]
        meta["CORNER_LR_PROJECTION_Y_PRODUCT"] = ast.literal_eval(
            sm["GridStructure"]["GRID_1"]["LowerRightMtrs"]
        )[1]

        return meta


class VIIRS(Strategy):

    def __init__(self, infile: str = "") -> None:
        assert infile != ""
        self._infile = infile

    def load(self) -> np.ndarray:
        import cv2

        # The output of 'load()' is (band, y, x) data with fractional values (eg 0.1329)
        # VNP band names are like
        #   SurfReflect_M3_1 type 'short' size (1200,1200) with scale_factor 0.0001
        #   SurfReflect_I3_1 type 'short' size (2400,2400) with scale_factor 0.0001
        #   sur_refl_b03_1  and is 'short' of size (2400,2400) with scale_factor 0.0001

        # Band correspondences:
        #   VNP/VJ1     band nums = [3, 4, 5, 7, 8, 10, 11]
        #   MOD09GA     band nums = [3, 4, 1, 2, 5,  6,  7]

        #band_nums = [3, 4, 5, 7, 8, 10, 11]  # Only have 7 SLI bands for now
        #band_names = ["SurfReflect_M" + str(n) + "_1" for n in band_nums]
        #data = np.zeros((len(band_nums), 1200, 1200), dtype=np.float32)

        # Explicitly list the band_names because we are (potentially) mixing inputs
        #   of different resolutions
        # Note:
        #   Band names of "_M<n>..." are 1000m fields (1200x1200)
        #   Band names of "_I<n>..." are  500m fields (2400x2400)
        band_names = [
            "SurfReflect_M3_1",
            "SurfReflect_M4_1",
            "SurfReflect_M5_1",
            "SurfReflect_I2_1",  # replaces M7
            "SurfReflect_M8_1",
            "SurfReflect_I3_1",  # replaces M10
            "SurfReflect_M11_1",
        ]
        data_1km = np.zeros((1200, 1200), dtype=np.float32)
        data_nbands_500m = np.zeros((len(band_names), 2400, 2400), dtype=np.float32)

        # TODO:
        #  - after reading all in, verify that data exists in rescaled fields
        #       at same grid cells that have data in native-500m fields (because
        #       rescaling might not work perfectly at -180/180 longitude boundary)
        # xarray methodology...
        # Note: xarray can open files with 'groups', but you have to specify the group
        #       hierarchy at the time of opening the file.  It does not appear to be
        #       discoverable from within xarray.  
        #       (Note: Newer xr.open_datatree() functionality might be applicable?)
        xdim_500m = 2400
        ydim_500m = 2400
        xdim_1km = 1200
        ydim_1km = 1200

        # TODO: Replace print() statements with logging, or delete them
        print(f'about to read from the HDF5 file: {self._infile}', flush=True)
        with xr.open_dataset(self._infile, group='/HDFEOS/GRIDS/VIIRS_Grid_1km_2D/Data Fields') as ds1km:
            with xr.open_dataset(self._infile, group='/HDFEOS/GRIDS/VIIRS_Grid_500m_2D/Data Fields') as ds500m:
                for i, band_name in enumerate(band_names):
                    if 'SurfReflect_I' in band_name:
                        # Read the native 500m data directly into the final array
                        ds_var_500m = ds500m[band_name]
                        assert ds_var_500m.shape == (ydim_500m, xdim_500m)
                        data_nbands_500m[i, :, :] = ds_var_500m.data[:, :]
                        print(f'Read in native 500m data from {band_name=}...', flush=True)
                    elif 'SurfReflect_M' in band_name:
                        # Read the native 1km data and rescale to 500m
                        ds_var_1km = ds1km[band_name]
                        data_1km = ds_var_1km.data[:, :]
                        assert ds_var_1km.shape == (ydim_1km, xdim_1km)

                        # Now, rescale this data from 1km to 500m using OpenCV's resize()
                        resized_data = np.zeros((ydim_500m, ydim_500m), dtype=data_1km.dtype)
                        resized_data[:, :] = cv2.resize(data_1km[:, :], (ydim_500m, xdim_500m))
                        data_nbands_500m[i, :, :] = resized_data[:, :]
                        print(f'Read in 1km data from {band_name=} and rescaled to 500m...', flush=True)
                    else:
                        raise ValueError('Do not know how to handle {band_name}')

                    n_unique_values = np.unique(data_nbands_500m[i, :, :]).shape[0]
                    print(f'num unique values for {band_name=}: {n_unique_values}')

        print('we should have data_nbands_500m(7, 2400, 2400) here (!)', flush=True)

        # TODO: Now, we need to ensure that the resized data fields have the same
        #       original-data as the native 500m data fields

        print('WARNING: tiles at edge-of-earth might have NaN mismatch')
        print('  between native 500m and rescaled-1km data fields', flush=True)

        # return resized_data
        return data_nbands_500m


    def SCAG_meta(self) -> pd.Series:

        meta["SOURCE_FILE"] = str(self._infile.resolve())
        meta["NBANDS"] = "7"
        meta["SENSOR"] = "VIIRS"
        meta["PROJ_STRING"] = "+proj=sinu +R=6371007.181 +nadgrids=@null +wktext"
        meta["DATUM"] = "WGS84"
        meta["ZONE_NUMBER"] = "N/A"
        meta["ELLIPSOID"] = "N/A"

        with h5py.File(self._infile, "r") as f:
            # am = self.parse_hdfeos_metadata(ds.attrs["ArchiveMetadata.0"])
            # cm = self.parse_hdfeos_metadata(ds.attrs["CoreMetadata.0"])
            sm = self.parse_hdfeos_metadata(
                f["HDFEOS INFORMATION"]["StructMetadata.0"][()].decode()
            )

            # TODO: Make this "related" to the resizing of the data...
            # We are overwriting the in-file dimensions with our
            #   resized dimensions.
            #meta["NLINES"] = sm["GridStructure"]["GRID_1"]["XDim"]
            #meta["NSAMPLES"] = sm["GridStructure"]["GRID_1"]["YDim"]
            file_nlines = sm["GridStructure"]["GRID_1"]["XDim"]
            file_nsamples = sm["GridStructure"]["GRID_1"]["YDim"]
            meta["NLINES"] = 2400
            meta["NSAMPLES"] = 2400

            sza = f["HDFEOS"]["GRIDS"]["VIIRS_Grid_1km_2D"]["Data Fields"][
                "SolarZenith_1"
            ][()]

            #meta["SUN_ZENITH"] = (
            #    sza[int(meta["NLINES"]) // 2, int(meta["NSAMPLES"]) // 2] / 100
            #)  # range appears to be scaled by 100 # CHECKME
            # TODO: This needs to be scaled by the file information, not the
            #       new (resized) metadata.
            meta["SUN_ZENITH"] = (
                sza[int(file_nlines) // 2, int(file_nsamples) // 2] / 100
            )  # range appears to be scaled by 100 # CHECKME

            meta["GRID_CELL_SIZE_REFLECTIVE"] = f.attrs["CharacteristicBinSize1KM"]
            meta["CORNER_UL_PROJECTION_X_PRODUCT"] = ast.literal_eval(
                sm["GridStructure"]["GRID_1"]["UpperLeftPointMtrs"]
            )[0]
            meta["CORNER_UL_PROJECTION_Y_PRODUCT"] = ast.literal_eval(
                sm["GridStructure"]["GRID_1"]["UpperLeftPointMtrs"]
            )[1]
            meta["CORNER_LR_PROJECTION_X_PRODUCT"] = ast.literal_eval(
                sm["GridStructure"]["GRID_1"]["LowerRightMtrs"]
            )[0]
            meta["CORNER_LR_PROJECTION_Y_PRODUCT"] = ast.literal_eval(
                sm["GridStructure"]["GRID_1"]["LowerRightMtrs"]
            )[1]

            # NOTE: ZONE_NUMBER is tile_ID
            # Typical file name is:
            #  VNP09GA_NRT.A2026042.h29v13.002.2026043041729.h5
            #      [0]       [1]     [2]   ...
            stem_split = Path(self._infile).stem.split(".")
            meta["ZONE_NUMBER"] = stem_split[2]

        return meta


class HLS(Strategy):
    # We treat HLS data as OLI. Reading is HLS-specific, but the META file
    # contains OLI metadata. Things seem to work correctly.
    def __init__(self, infile: str = "") -> None:
        assert infile != ""
        self._infile = infile

    def load(self) -> np.ndarray:
        # See HLS_User_Guide_V2.pdf Table 3 "HLS spectral bands nomenclature"
        band_names = []
        if "L30" in str(self._infile):
            band_names = ["B02", "B03", "B04", "B05", "B06", "B07"]
        if "S30" in str(self._infile):
            band_names = ["B02", "B03", "B04", "B8A", "B11", "B12"]
        assert band_names != []

        bands = []
        for i, n in enumerate(band_names):
            raster = glob.glob(str(self._infile) + os.path.sep + "HLS.*" + n + ".tif")
            assert len(raster) == 1
            raster = raster[0]
            b = rxr.open_rasterio(raster, masked=True).squeeze()

            b = b.where(b != 0, other=np.nan)
            b = b * b.scale_factor + b.add_offset
            bands.append(b)
            bands[i]["band"] = i

        ds = xr.concat(bands, dim="band")
        data = ds.to_dataset(name="BIP").to_array().data.squeeze()
        return data

    def SCAG_meta(self) -> pd.Series:
        raster = glob.glob(str(self._infile) + os.path.sep + "HLS.*SZA.tif")[0]
        b = rxr.open_rasterio(raster, masked=True).squeeze()

        meta["SOURCE_FILE"] = str(self._infile.resolve())
        meta["NBANDS"] = "6"
        meta["SENSOR"] = "OLI"
        meta["NLINES"] = len(b.y)
        meta["NSAMPLES"] = len(b.x)

        meta["SUN_ZENITH"] = (
            b[int(len(b.x) / 2), int(len(b.y) / 2)] * b.scale_factor
        ).data

        stem_split = Path(self._infile).stem.split(".")
        meta["ZONE_NUMBER"] = stem_split[2][1:3]  # + stem_split[2][0]
        meta["ELLIPSOID"] = "WGS84"
        meta["DATUM"] = "WGS84"
        meta["GRID_CELL_SIZE_REFLECTIVE"] = (b.x[1] - b.x[0]).values
        meta["PROJ_STRING"] = (
            "+proj=utm +zone="
            + meta["ZONE_NUMBER"]
            + " +datum="
            + meta["DATUM"]
            + " +units=m +no_defs +ellps="
            + meta["ELLIPSOID"]
        )
        meta["CORNER_UL_PROJECTION_X_PRODUCT"] = b.x[0].data
        meta["CORNER_UL_PROJECTION_Y_PRODUCT"] = b.y[0].data
        meta["CORNER_LR_PROJECTION_X_PRODUCT"] = b.x[-1].data
        meta["CORNER_LR_PROJECTION_Y_PRODUCT"] = b.y[-1].data
        return meta


class Landsat(Strategy):
    def __init__(self, infile: str = "") -> None:
        assert infile != ""
        self._infile = infile

    def load(self) -> np.ndarray:

        json_file = glob.glob(str(self._infile) + os.path.sep + "*_MTL.json")
        with open(json_file[0], "r") as myfile:
            data = myfile.read()
        mtl = json.loads(data)["LANDSAT_METADATA_FILE"][
            "LEVEL2_SURFACE_REFLECTANCE_PARAMETERS"
        ]

        bands = []
        for n, i in enumerate(range(2, 7 + 1)):
            istr = str(i)
            raster = glob.glob(
                str(self._infile) + os.path.sep + "*_SR_B" + istr + ".TIF"
            )
            assert len(raster) == 1
            raster = raster[0]
            b = rxr.open_rasterio(raster, masked=True).squeeze()

            b = b.where(b != 0, other=np.nan)
            mult = np.array([mtl["REFLECTANCE_MULT_BAND_" + istr]]).astype(np.float64)[
                0
            ]
            add = np.array([mtl["REFLECTANCE_ADD_BAND_" + istr]]).astype(np.float64)[0]
            b = b * mult + add
            b = b.where(b >= 0, other=0)

            bands.append(b)
            bands[n]["band"] = i  # Assign a band number to the new xarray object

        ds = xr.concat(bands, dim="band")
        data = ds.to_dataset(name="BIP").to_array().data.squeeze()
        return data

    def SCAG_meta(self) -> pd.Series:
        json_file = glob.glob(str(self._infile) + os.path.sep + "*_MTL.json")
        with open(json_file[0], "r") as myfile:
            data = myfile.read()
        mtl = json.loads(data)["LANDSAT_METADATA_FILE"]

        meta["SOURCE_FILE"] = str(self._infile.resolve())
        meta["NBANDS"] = "6"
        meta["SENSOR"] = "OLI"
        meta["NLINES"] = mtl["PROJECTION_ATTRIBUTES"]["REFLECTIVE_LINES"]
        meta["NSAMPLES"] = mtl["PROJECTION_ATTRIBUTES"]["REFLECTIVE_SAMPLES"]
        meta["SUN_ZENITH"] = 90 - float(mtl["IMAGE_ATTRIBUTES"]["SUN_ELEVATION"])

        meta["ZONE_NUMBER"] = mtl["PROJECTION_ATTRIBUTES"]["UTM_ZONE"]
        meta["ELLIPSOID"] = mtl["PROJECTION_ATTRIBUTES"]["ELLIPSOID"]
        meta["DATUM"] = mtl["PROJECTION_ATTRIBUTES"]["DATUM"]
        meta["PROJ_STRING"] = (
            "+proj=utm +zone="
            + meta["ZONE_NUMBER"]
            + " +datum="
            + meta["DATUM"]
            + " +units=m +no_defs +ellps="
            + meta["ELLIPSOID"]
        )

        cell_size = float(mtl["PROJECTION_ATTRIBUTES"]["GRID_CELL_SIZE_REFLECTIVE"])
        meta["GRID_CELL_SIZE_REFLECTIVE"] = cell_size
        meta["CORNER_UL_PROJECTION_X_PRODUCT"] = (
            float(mtl["PROJECTION_ATTRIBUTES"]["CORNER_UL_PROJECTION_X_PRODUCT"])
            - cell_size / 2
        )
        meta["CORNER_UL_PROJECTION_Y_PRODUCT"] = (
            float(mtl["PROJECTION_ATTRIBUTES"]["CORNER_UL_PROJECTION_Y_PRODUCT"])
            + cell_size / 2
        )
        meta["CORNER_LR_PROJECTION_X_PRODUCT"] = (
            float(mtl["PROJECTION_ATTRIBUTES"]["CORNER_LR_PROJECTION_X_PRODUCT"])
            + cell_size / 2
        )
        meta["CORNER_LR_PROJECTION_Y_PRODUCT"] = (
            float(mtl["PROJECTION_ATTRIBUTES"]["CORNER_LR_PROJECTION_Y_PRODUCT"])
            - cell_size / 2
        )

        return meta


class BIPifier_drfs:
    """BIPifier class

    Converts various satellite data products
    (e.g., raster stack with dimensions (band,x,y))
    to a Band Interleaved Pixel (BIP) binary file
    (e.g., (x,y,band))
    """

    def __init__(self, infile=None, data_source: Strategy = None):
        assert data_source is not None
        assert infile != ""

        self._indata: np.ndarray
        self._BIPdata: np.ndarray
        self._infile = infile  # input filename or numpy array
        self._data_source = data_source
        self._data_source.__init__(self, infile=self._infile)

    def load(self, data: np.ndarray = None):
        """Load file using the data_source Strategy"""
        self._indata = self._data_source.load(self)

        # This will return None if not implemneted by the strategy.
        self._SCAG_meta = self._data_source.SCAG_meta(self)
        return self

    def BIPify_for_DRFS(self):
        """BIPify data:  Accomplishes two tasks:
           1. Converts data to band-interleaved-pixel (BIP) format
              where the last index indicates the field
           2. Scales floating points by a factor of 1000 and changes
              dtype to int16

        Note: This version implements the logic of the DRFS code from scagdrfs_jpl
          The differences between this and the SCAG bipify are:
            1. The dtype is int16 instead of uint16
            2. NaNs are explicitly set (re-set?) to -2866
            3. Values of -10 to -1 are allowed, instead of being set to zero

        A fractional percentage,
          eg 0.2478
          is converted to an unsigned int representation
          scaled by a factor of 1000

        So, input of 0.2478 becomes 245
          (ia 0.2478 * 1000 => 247.8  + 0.5  => 248.3  => "floor int" => 248

        """
        self._BIPdata = self._indata.transpose(1, 2, 0)

        # The BIP'ified data is manually scaled by a factor of 1000 and
        #    converted to unsigned short ints
        tmp = self._BIPdata * 1e3 + 0.5
        data_isnan = np.isnan(tmp)
        n_isnan = np.sum(np.where(data_isnan, 1, 0))
        print(f'Number of NaN values: {n_isnan}')
        if tmp.min() < -10:
            print(f'WARNING: Unexpectedly low reflectance value: {tmp.min()}')

        if tmp.max() > MAX_INT16:
            print(f'WARNING: Unexpectedly high reflectnace value(s): {tmp.max()}')
            print('   Clipping to {MAX_INT16}')
            tmp[tmp > MAX_INT16] = MAX_INT16

        # Here, we explicitly set NaN values to -2866 because this is what the
        #  original DRFS IDL code did
        if n_isnan > 0:
            NaN_bip_value_DRFS = -2866
            print('  Note: explicitly setting these NaN values to {NaN_bip_value_DRFS=}')
            tmp[np.isnan(tmp)] = NaN_bip_value_DRFS
            data_as_int16 = tmp.astype(np.int16)
            nan_as_int16 = np.unique(data_as_int16[data_isnan])
            print(f'unique int16 values that were originally NaNs: {nan_as_int16}')

        # We have found that after scaling by 1000, the data should
        #   have a maximum value of about 1600.
        max_data_value = data_as_int16.max()
        if max_data_value > 2000:
            raise ValueError(f'_BIPdata should not be higher than 2000: {max_data_value}')

        self._BIPdata = data_as_int16

        return self

    def write_BIP(self, outfile: Path = None) -> None:
        """Write BIP data to disk"""
        assert outfile is not None

        outdir = outfile.parent
        outdir.mkdir(parents=True, exist_ok=True)

        self._BIPdata.tofile(outfile)

        # If the strategy provided metadata, save it.
        if self._SCAG_meta is not None:
            outfilename = str(outfile) + ".meta"
            pd.DataFrame(self._SCAG_meta).to_csv(
                outfilename, index=True, sep="=", header=False
            )

    # Used by MODIS and VIIRS
    def parse_hdfeos_metadata(self, string):
        # from https://github.com/SpatioTemporal/STAREMaster_py/blob/ \
        # af5cba54b55194fefae1448b5a6de1279b05fd22/staremaster/products/hdfeos.py
        # LICENSE should be OK:
        # https://github.com/SpatioTemporal/STAREMaster_py/issues/31

        out = {}
        lines0 = [i.replace("\t", "") for i in string.split("\n")]
        lines = []
        for line in lines0:
            if "=" in line:
                key = line.split("=")[0]
                value = "=".join(line.split("=")[1:])
                lines.append(key.strip() + "=" + value.strip())
            else:
                lines.append(line)
        i = -1
        while i < (len(lines)) - 1:
            i += 1
            line = lines[i]
            if "=" in line:
                key = line.split("=")[0]
                value = "=".join(line.split("=")[1:])  # .join('=')
                if key in ["GROUP", "OBJECT"]:
                    endIdx = lines[i + 1 :].index("END_{}={}".format(key, value))
                    endIdx += i + 1
                    out[value] = self.parse_hdfeos_metadata(
                        "\n".join(lines[i + 1 : endIdx])
                    )
                    i = endIdx
                elif ("END_GROUP" not in key) and ("END_OBJECT" not in key):
                    out[key] = str(value)
        return out


def get_data_source(input_filename: str):
    if re.compile(r"\S+MOD09GA\S+").match(input_filename):
        data_source = MOD09GA
    elif re.compile(r"\S+(VNP|VJ1)\S+").match(input_filename):
        data_source = VIIRS
    elif re.compile(r"(VNP|VJ1)\S+").match(input_filename):
        data_source = VIIRS
    elif re.compile(r"\S+HLS\S+").match(input_filename):
        data_source = HLS
    elif re.compile(r"\S+LC\S+").match(input_filename):
        data_source = Landsat
    elif re.compile(r"MOD09GA\S+").match(input_filename):
        data_source = MOD09GA
    else:
        raise Exception(f"Reader not found for this file type {input_filename=}")
    return data_source


def bipify_file_drfs(input_file, output_file):
    data_source = get_data_source(str(input_file))

    bf = BIPifier_drfs(infile=input_file, data_source=data_source)
    bf.load().BIPify_for_DRFS()
    bf.write_BIP(output_file)
    print(f'just wrote BIP file: {output_file}')
    breakpoint()
    # bf.write_GeoTIF(args.outfile.with_suffix(".tif"))


def parse_arguments():
    parser = ArgumentParser(description="BIPifier_drfs")

    # TODO: https://docs.python.org/3/library/argparse.html#filetype-objects
    parser.add_argument(
        "-i", "--infile", type=Path, required=True, help="Name of input file"
    )
    parser.add_argument(
        "-o",
        "--outfile",
        default="",
        type=Path,
        required=True,
        help="Name of output file.",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    """Executed from the command line"""
    args = parse_arguments()
    bipify_file_drfs(args.infile, args.outfile)

else:
    """Executed on import"""
    pass
