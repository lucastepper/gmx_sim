import shlex
import subprocess
from pathlib import Path
from typing import Optional, Union


class GromacsEnv(dict):
    """A class to hold the environment variables for the gromacs version in use."""

    def __init__(
        self,
        gromacs_version: str,
        gmx_force_fields: str = "/net/storage/greedisgod/force_fields_gmx",
    ):
        super().__init__()
        proc = subprocess.run(
            shlex.split(
                "/usr/bin/sh -c '. /etc/profile && module purge && "
                f"module load {gromacs_version} && env'"
            ),
            check=True,
            capture_output=True,
        )
        out = proc.stdout.decode("utf-8").split("\n")
        self.env = {}
        for line in out:
            if "gromacs" in line:
                key, item = line.split("=")
                self[key] = item
        self.clean_path()
        self["GMXLIB"] = gmx_force_fields

    def clean_path(self):
        """Kick all but the explicit directory to gmx, make sure it is only one."""
        path = self["PATH"]
        gmx_path = None
        for sub_path in path.split(":"):
            if "gromacs" in sub_path or "gmx" in sub_path:
                if gmx_path is None:
                    gmx_path = sub_path
                else:
                    raise ValueError(f"Found two matches for gromacs in PATH: {path}")
        self["PATH"] = gmx_path


def run_subprocess(
    command: str,
    env: dict[str, str],
    output_file: Optional[Union[str, Path]] = None,
    verbose: bool = False,
):
    """Run a subprocess with a given environment in a shell. If it fails, print the output
    always print to console and optionally to file. If it succeeds, optionally print to console
    and/or file.
    Args:
        command (str): The command to run
        env (dict[str, str]): The environment to run the command in
        output_file (str, Path): The file to write the output to. Default: None.
        verbose (bool): Whether to print the output to console. Default: False.
    """
    stdout_mode = subprocess.PIPE
    stderr_mode = subprocess.STDOUT
    if output_file:
        # pylint: disable=consider-using-with
        output_stream = open(output_file, "w", encoding="utf-8")
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
        if output_file:
            output_stream.write(process.stdout)
    # handle errors
    except subprocess.CalledProcessError as e:
        # Print the output optionally to file, always to console
        if output_file:
            output_stream.write(e.stdout)
        print(e.stdout)
    finally:
        # Close the output stream if it was opened
        if output_file:
            output_stream.close()
