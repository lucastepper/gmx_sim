# pylint: disable=logging-fstring-interpolation
import subprocess
from pathlib import Path
from typing import Optional, Union
import difflib
import gmx_sim
from utils import to_path
import logging
from utils import FileCreationLogger
from gmx_subprocess import run_subprocess


def check_force_field(force_field: str) -> str:
    """Check if the forcefield exists in either $GMXDATA/top or $GMXLIB or cwd.
    If not, find all available force fields, look for the closest match and
    ask if the user wants to use it."""
    if not force_field.endswith(".ff"):
        force_field += ".ff"
    # find all available force fields
    env = gmx_sim.get_env()
    path_list = [Path(env["GMXDATA"]) / "top", Path(env["GMXLIB"]), Path(".")]
    ff_names = []
    for path in path_list:
        if (path := Path(path).resolve()).is_dir():
            ff_names.extend([f.name for f in path.glob("*.ff")])
    # check if the force field exists, if not find the closest match and ask for input
    if force_field not in ff_names:
        closest_match = difflib.get_close_matches(force_field, ff_names, n=1)[0]
        print(f"Could not find {force_field=} in $GMXDATA/top, $GMXLIB or cwd.")
        accepted = input(f"Did you mean {closest_match}? [y/n]")
        if not accepted.lower() == "y":
            raise ValueError("Could not find force field.")
        force_field = closest_match
    return force_field.removesuffix(".ff")


def pdb2gmx(
    pdb_file: Path,
    force_field: str,
    water: str,
    outfile: Optional[str] = None,
    ignh: bool = False,
    verbose: bool = False,
    logfile: Optional[str] = "pdb2gmx.out",
):
    """Convert a pdb file to a gromacs topology file."""
    logging.info(f"Running pdb2gmx with {pdb_file=}")
    pdb_file = to_path(pdb_file)
    if not pdb_file.is_file():
        raise ValueError(f"Could not find {pdb_file=}")
    check_force_field(force_field)
    # I cant automatically check for water, was it has either .itp or .gro extension
    # and other files might have the same extension.
    if not outfile:
        outfile = pdb_file.stem
    else:
        outfile = Path(outfile).stem + ".gro"
    command = f"gmx pdb2gmx -f {pdb_file} -o {outfile} -ff {force_field} -water {water}"
    if ignh:
        command += " -ignh"
    with FileCreationLogger():
        run_subprocess(command, gmx_sim.get_env(), verbose=verbose, out_file=logfile)
    logging.info(f"Finished pdb2gmx with {outfile=}")
