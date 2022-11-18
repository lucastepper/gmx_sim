import os
import shlex 
import subprocess


def set_gmx_path(logger, config) -> None:
    """ Set up environ such that it contains the gromacs given in config. """

    if "gmxpath" in config:
        if not os.path.isfile((gmxpath := config["gmxpath"])):
            raise FileNotFoundError("Path to GMXRC not found.")
        # logging.info(f"Loading gmx: {gmxpath}")
        logger.info(f"Loading gmx: {gmxpath}")
        command = shlex.split("env -i bash -c 'source {} && env'".format(gmxpath))
        to_add = subprocess.run(command, capture_output=True).stdout.decode()
        for line in to_add.split("\n"):
            if "GMX" in line:
                var_name, var = line.split("=")
                os.environ[var_name] = var
    if "gmxlib" in config:
        os.environ['GMXLIB'] = config['gmxlib']
        logger.info("Setting gmx lib: {}".format(config['gmxlib']))
    # TODO load module
    import gromacs


from gmx_sim.simulation import Simulation