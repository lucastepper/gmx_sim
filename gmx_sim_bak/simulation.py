import os
import sys
import shlex
import subprocess
import logging
from typing import Any
from collections import defaultdict
import difflib
import gromacs
import toml
import numpy as np


def setup_custom_logger(path, name="gmx_logger"):
    """ It is a LOGGER! """
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.FileHandler(path, mode="w")
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger


LOGGER = setup_custom_logger(os.path.join(os.getcwd(), "gmx_sim.log"))


class Config(dict):
    """ Config to store all inputs for simulaiton. """

    def __init__(self, config_file: str) -> None:
        super().__init__()
        if not os.path.isfile(config_file):
            raise FileNotFoundError(f"Config file: {config_file} not found.")
        self.ref_config = toml.load(os.path.dirname(__file__) + "/input_template.toml")
        config = toml.load(config_file)
        config = self.check_config(config)
        self.copy_into_super(config)

    def copy_into_super(self, config: dict) -> bool:
        """ Given a dict with subdicts, copy content into super. """
        for key, item in config.items():
            if isinstance(item, dict):
                self[key] = {}
                for sub_key, sub_item in item.items():
                    self[key][sub_key] = sub_item
            else:
                self[key] = item

    def get_input_replace_key(self, key: str, item: Any, subkey: str = None) -> str:
        """Given a (sub)key from config that is not in config_ref.
        If not, displays message, asking to replace (sub)key/item
        pair with closes match from config_ref."""

        message = (
            "In config, key: {} item: {} not found in "
            + "ref config did you mean {}? y/n?"
        )
        if subkey:
            ref_key = difflib.get_close_matches(subkey, self.ref_config[key].keys())
            if len(ref_key) == 0:
                raise ValueError(f"Key: {key}/{subkey} not found in reference toml.")
            else:
                ref_key = ref_key[0]
            input_y_n = input(message.format(f"{key}/{subkey}", item, ref_key))
            if input_y_n == "y":
                return ref_key
        else:
            ref_key = difflib.get_close_matches(key, self.ref_config.keys())[0]
            if len(ref_key) == 0:
                raise ValueError(f"Key: {key} not found in reference toml.")
            else:
                ref_key = ref_key[0]
            input_y_n = input(message.format(key, item, ref_key))
            if input_y_n == "y":
                return ref_key
        raise ValueError("Unknown key in config toml file.")

    def check_config(self, config: dict) -> dict:
        """Run through all keys in config and its subdicts and check
        if the keys are in the reference config toml file.
        If not, ask user to replace them with closest match."""

        # copy contend into new dict, as we cannot change during iteration
        config_new = {}
        for key, item in config.items():
            if isinstance(item, dict):
                config_new[key] = {}
                for sub_key, sub_item in item.items():
                    if sub_key not in self.ref_config[key]:
                        sub_key = self.get_input_replace_key(key, item, sub_key)
                    config_new[key][sub_key] = sub_item
            else:
                if key not in self.ref_config:
                    key = self.get_input_replace_key(key, item)
                config_new[key] = item
        return config_new


class SimFiles:
    """Wrapper to handle all file storages and log with ones are created.
    Used to find the currently relevant files for the simulation."""

    def __init__(self, path, autosave=True) -> None:
        self.path = path
        self.files_name = os.path.join(self.path, "files.toml")
        self.files = self.load_files_toml()
        self.minor_path = os.path.join(self.path, "simfiles")
        if not os.path.isdir(self.minor_path):
            os.mkdir(self.minor_path)
        # we sort files into the major path and minor path
        # based on file ending, with boring files in minor
        # all files not in major go in minor
        self.major_files = [".xtc"]

    def add_files(self, names: str) -> str:
        """Add names for files to internal file state.
        the appropriate save name. If file already exists,
        raises FileExistsError."""
        # convert all file names to corresponding paths
        file_paths = []
        for file_name in names:
            file_ending = file_name.split(".")[-1]
            if file_ending in self.major_files:
                file_path = os.path.join(self.path, file_name)
            else:
                file_path = os.path.join(self.minor_path, file_name)
            file_paths.append(file_path)
        # check if all paths exist, if such, signal not to run
        if np.all([os.path.exists(file_path) for file_path in file_paths]):
            return None
        # if some exist, back them up. Run through all and add them to self.files
        for file_path in file_paths:
            if os.path.exists(file_path):
                print("WARNING: some files existed already, some not, backing up.")
                logging.info(f"Backing up {file_path}")
                assert not os.path.exists(file_path + "bak")
                os.replace(file_path, file_path + "bak")
            self.files[file_ending].append(file_path)
        return file_paths

    def save(self) -> None:
        """ On save, stores all file types """
        for file_type_list in self.files:
            for file in file_type_list:
                if not os.path.isfile(file):
                    print(
                        f"WARNING: On saving expected {file} to exist but it was not found."
                    )
        # TODO maybe check that overwriting files.toml does not erase any keys
        with open(self.files_name, "w") as fh:
            toml.save(fh, self.files)

    def load_files_toml(self) -> defaultdict:
        """ Load files.toml from path. """
        files = defaultdict(list)
        if os.path.isfile(self.files_name):
            temp = toml.load(self.files_name)
            for file_type, file_type_list in temp:
                for file in file_type_list:
                    files[file_type].append(file)
        return files

    def set_output_file(self, command):
        """Set the output file for a gromacs command.
        Enter filename into logging. Check that no dublicates happen."""
        i = 0
        file_name = command + bool(i) * f"_{i}"
        while os.path.exists(file_name):
            i += 1
            file_name = command + bool(i) * f"_{i}"
        file_name = os.path.join(self.minor_path, file_name + '.out')
        LOGGER.info(f"Set file name for output of {command=} to {file_name}")
        gromacs.environment.flags["capture_output"] = "file"
        gromacs.environment.flags['capture_output_filename'] = file_name


class Simulation:
    """ Main class to handle the simulation. """

    def __init__(
        self, config_file: str, verbose: bool = True, logfile: str = None
    ) -> None:
        self.config = Config(config_file)
        self.verbose = verbose
        self.path = os.getcwd()
        self.files = SimFiles(self.path)
        # put all uninteresting files into minor path
        self.set_gmx_path()
        # import gromacs here so that gmx in path already
        import gromacs

    def set_gmx_path(self) -> None:
        """ Set up environ such that it contains the gromacs given in config. """
        if "gmxpath" in self.config:
            if not os.path.isfile((gmxpath := self.config["gmxpath"])):
                raise FileNotFoundError("Path to GMXRC not found.")
            # logging.info(f"Loading gmx: {gmxpath}")
            LOGGER.info(f"Loading gmx: {gmxpath}")
            command = shlex.split("env -i bash -c 'source {} && env'".format(gmxpath))
            to_add = subprocess.run(command, capture_output=True).stdout.decode()
            for line in to_add.split("\n"):
                if "GMX" in line:
                    var_name, var = line.split("=")
                    os.environ[var_name] = var
        if "gmxlib" in self.config:
            os.environ['GMXLIB'] = self.config['gmxlib']
            LOGGER.info("Setting gmx lib: {}".format(self.config['gmxlib']))
        # TODO load module

    def pdb2gmx(self) -> None:
        """ Generate topology from pdb file. """

        pdb_file = self.config["pdb2gmx"]["pdbfile"]
        if not os.path.isfile(pdb_file):
            raise ValueError("pdb file not found")
        LOGGER.info(f"Converting {pdb_file} to gmx.")
        file_paths = self.files.add_files(
            ["conf_pdb.gro", "topol_vac.top", "posre.itp"]
        )
        if file_paths is None:
            LOGGER.info("Found output for pdb2gmx already, skipping.")
            return
        else:
            gmx_io_kwargs = dict(zip(["o", "p", "i"], file_paths))
        # configure piping stdout/err to file and run command
        self.files.set_output_file("pdb2gmx")
        gromacs.pdb2gmx(
            f=os.path.join(self.path, pdb_file),
            ff=self.config["pdb2gmx"]["forcefield"],
            water=self.config["pdb2gmx"]["water"],
            ignh=True,
            **gmx_io_kwargs,
        )
        if not np.all([os.path.exists(file) for file in file_paths]):
            raise ValueError("pdb2gmx not successful")

    def energy_minimization_vaccum(self):
        raise NotImplementedError()

    def energy_minimization(self):
        raise NotImplementedError()

    def simulate(self):
        raise NotImplementedError()


# config = Config('gmx_sim/example_input.toml')
# print(config)

# sim = Simulation(sys.argv[1])
os.chdir("/net/data04/greedisgod/ala9_changes/ala9_uncharged")
sim = Simulation(
    "/net/data04/greedisgod/ala9_changes/ala9_uncharged/gmx_sim_input.toml"
)
# print(sim.config)
sim.pdb2gmx()
# sim.files.save()

# print(sim.config)
