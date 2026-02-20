#!/usr/bin/env python


from pathlib import Path

from scag.scripts.BIPifier import bipify_file


def bipify_files(input_dir: Path, output_dir: Path):
    """Transforms the input files specified into BIP (Band Interleaved by Pixel)
    files scag and drfs can process.

    Args:
        input_dir (Path): The directory containing input files to be transformed.
        output_dir (Path): The directory where transformed files will be saved.

    Returns:
        str: A success message indicating that the BIP files have been created.
    """
    for input_file in input_dir.glob("**/*.h5"):
        outfile = output_dir / input_file.with_suffix(".bip").name
        bipify_file(input_file, outfile)

    return "Bip files created"
