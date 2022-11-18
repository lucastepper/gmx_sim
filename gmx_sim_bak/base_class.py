import os
import sys
import subprocess
import logging
import toml


def GMXProcess(subprocess.CompletedProcess):
    """ Small wrapper to encode stdout and stderr. """

    def __init__(self, command):
        """ Given the command as a string, return a completed process, where 
        the stdout/err have been decoded split into lines and striped of new lines
        Also, accept whitespace separated intput as bash does."""
        if isinstance(command, str):
            command = command.split()
        assert np.all([isinstance(entry, str) for entry in command])
        proc = subprocess.run(env=os.environ.copy(), capture_output=True, check=True)
        super.__init__(
            returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, args=proc.args
        )
        self.stdout = [x for x in proc.stdout.decode().split('\n')]
        self.stderr = [x for x in proc.stderr.decode().split('\n')]

class GMXSimBase():
    """ Base class to handle calling gromacs command line programs. """

    def __init__(self, config=None, logfile=None):
        """ Parse a config file, if given. """
        # TODO give config a better name, something like user_script
        self.config_path = config
        if logfile is None:
            logging.basicConfig(filename='gmx_sim.log', level=logging.INFO)
        self.config = {}
        # TODO log stuff
        if config is not None:
            with open(config) as fh:
                for key, item in fh.items():
                    config[key] = item

    def set_gmx_env(self, gmx_path=None, gmx_lib=None):
        """ If gmx_path not given as arg or in config, raise error.
        Arg takes precedent. Lib path not needed Check that gmx works. """
        # TODO write better Warning.
        # TODO log stuff
        os.environ['GMXLIB'] = self.config.get('gmx_lib')
        if gmx_lib is not None and 'gmx_lib' in self.config:
            print('Warning: Overwriting value for GMXLIB from config with user input.')
            os.environ['GMXLIB'] = gmx_lib
        os.environ['GMXLIB'] = self.config.get('gmx_lib')
        if gmx_lib is not None and 'gmx_lib' in self.conf

    def set_gmx_path(self, path):
        """ Source RC for GMX and check that it runs. """
        if path.endswith('GMXRC'):
            assert os.path.isfile(path), f'Path to GMXRC {path} is not valid.'
            os.system(f'source {path}')
        elif os.path.isfile(os.path.join(path, 'GMXRC')):
            os.system(f'source {os.path.join(path, 'GMXRC')}')
        else:
            raise ValueError(f'Given path {path} not valid.')
        assert run_command

    def get_gmx_version(self):
        proc = GMXProcess('gmx version')
        self.run_command('gmx version')[0]