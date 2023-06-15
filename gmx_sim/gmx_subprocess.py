import subprocess
from pathlib import Path
from typing import Optional, Union
import gmx_sim


class GromacsEnv(dict):
    """A class to hold the environment variables for the gromacs version in use."""

    def __init__(
        self,
        gromacs_executable: Optional[str] = None,
        gromacs_module: Optional[str] = None,
        clean_path: bool = None,
        gmx_lib: str = "/net/storage/greedisgod/force_fields_gmx",
    ):
        super().__init__()
        if gromacs_executable is None and gromacs_module is None:
            gromacs_executable = "gmx"

        if gromacs_executable is not None:
            # check if gmx_executable already in the environment
            if (
                subprocess.run(
                    f"{gromacs_executable} --version", shell=True, check=True, capture_output=True
                ).returncode
                == 0
            ):
                command = "env"
            # check if gmx_executable is a path
            elif (gmx_exe := Path(gromacs_executable)).is_file():
                command = f". {gmx_exe.parent / 'GMXRC'} && env"
            else:
                raise ValueError(f"Could not find gromacs executable: {gromacs_executable}")
        else:
            command = "/usr/bin/sh -c '. /etc/profile && module purge && "
            command += f"module load {gromacs_module} && env'"
        proc = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
        )
        out = proc.stdout.decode("utf-8").split("\n")
        for line in out:
            if "gromacs" in line or "GMX" in line:
                key, item = line.split("=")
                self[key] = item
            if "PATH" in line:
                key, item = line.split("=")
                self[key] = item
        if clean_path:
            self.clean_path()
        self["GMXLIB"] = gmx_lib

    def clean_path(self):
        """Kick all but the explicit directory to gmx, make sure it is only one."""
        path = self["PATH"]
        gmx_path = None
        for sub_path in path.split(":"):
            if "gromacs" in sub_path or "gmx" in sub_path or "GMX" in sub_path:
                if gmx_path is None:
                    gmx_path = sub_path
                else:
                    raise ValueError(f"Found two matches for gromacs in PATH: {path}")
        if gmx_path:
            self["PATH"] = gmx_path
        else:
            raise ValueError(f"Could not find gromacs in PATH: {path}")

def set_env(
    gromacs_executable: Optional[str] = None,
    gromacs_module: Optional[str] = None,
    clean_path: bool = None,
    gmx_lib: str = "/net/storage/greedisgod/force_fields_gmx",
):
    """Set the gmx module to use in following simulations.
    Args:
        gmx_module (str): Name of the tcl module to load
        gmx_force_filed (str): Path to GMXLIB, where force-fields are stored.
    """
    gmx_sim.GMXENV = GromacsEnv(gromacs_executable, gromacs_module, clean_path, gmx_lib)


def get_env() -> GromacsEnv:
    """ Automatically set the gmx env, if not already there to use in following simulations."""
    if gmx_sim.GMXENV is None:
        gmx_sim.GMXENV = GromacsEnv()
    return gmx_sim.GMXENV


def run_subprocess(
    command: str,
    env: dict[str, str],
    out_file: Optional[Union[str, Path]] = None,
    verbose: bool = False,
):
    """Run a subprocess with a given environment in a shell. If it fails, print the output
    to console and optionally to file. If it succeeds, optionally print to console
    and/or file.
    Args:
        command (str): The command to run
        env (dict[str, str]): The environment to run the command in
        out_file (str, Path): The file to write the output to. Default: None.
        verbose (bool): Whether to print the output to console. Default: False.
    """
    stdout_mode = subprocess.PIPE
    stderr_mode = subprocess.STDOUT
    if out_file:
        # pylint: disable=consider-using-with
        output_stream = open(out_file, "w", encoding="utf-8")
    try:
        # Run the command
        process = subprocess.run(
            command,
            shell=True,
            env=env,
            stdout=stdout_mode,
            stderr=stderr_mode,
            universal_newlines=True,
            check=True,
        )
        # Print the output optionally to file and/or console
        if verbose:
            print(process.stdout)
        if out_file:
            output_stream.write(process.stdout)
    # handle errors
    except subprocess.CalledProcessError as e:
        # Print the output optionally to file, always to console
        if out_file:
            output_stream.write(e.stdout)
        print(e.stdout)
    finally:
        # Close the output stream if it was opened
        if out_file:
            output_stream.close()
