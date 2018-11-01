# -*- coding: utf-8 -*-
import sys
import os
import argparse
from subprocess import Popen, PIPE
from vmaker.init.config import ConfigController
from vmaker.init.plugins import PluginController
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM


class Engine(object):
    """ Class controls prerun of the program
        - Parse command-line arguments
        - Execute config module
        - Execute plugins module
        - Creating PID file
        - Creating Session file
        - Control session
        """
    _SESSION_FILE = LoadSettings.SESSION_FILE
    _PID_FILE = LoadSettings.PID_FILE
    _GENERAL_CONFIG = LoadSettings.GENERAL_CONFIG
    _CONFIG_FILE = LoadSettings.CONFIG_FILE_PATH

    def __init__(self):
        # Check if one instance of the program is already running.
        self.check_running_state()
        # Parse command-line arguments.
        self.args()
        config = ConfigController(self._CONFIG_FILE)
        # Load user configuration file and sequence to move on.
        self.config, self.config_sequence = config.load_config()
        # Check and load plugins.
        self.loaded_plugins = PluginController(LoadSettings.ENABLED_PLUGINS).load_plugins()
        self.check_attributes_dependencies()

    def check_attributes_dependencies(self):
        STREAM.info("==> Checking for plugins required attributes.")
        for vm in self.config_sequence:
            # Set of required attributes for all Keywords used in the VirtualMachine
            req_args = set()
            STREAM.debug("==> VirtualMachine: %s" % vm)
            for action in self.config[vm].actions:
                try:
                    # List of required attributes for the Keyword to work
                    req_attr = self.loaded_plugins[action].REQUIRED_CONFIG_ATTRS
                    # Add required attributes of current action to summary set
                    req_args = set(req_args) | set(req_attr)
                except KeyError:
                    try:
                        # Check aliases actions for required attributes
                        for act in self.config[vm].aliases[action]:
                            req_attr = self.loaded_plugins[act].REQUIRED_CONFIG_ATTRS
                            req_args = set(req_args) | set(req_attr)
                    except KeyError as key:
                        STREAM.error("The plugin (%s) you use in the configuration file does not exist or is not enabled." % key)
                        STREAM.warning("You can't use this plugin until you turn it on in .vmaker.ini")
                        sys.exit(1)
                    except AttributeError:
                        STREAM.error("The plugin (u'%s') you use in the configuration file does not exist or is not enabled." % action)
                        STREAM.warning("You can't use this plugin until you turn it on in .vmaker.ini")
                        sys.exit(1)
            vm_attrs = [name for name in dir(self.config[vm]) if not name.startswith('__')]
            req_args = set(req_args)
            vm_attrs = set(vm_attrs)
            STREAM.debug(" -> required attributes: %s" % req_args)
            STREAM.debug(" -> VirtualMachines attributes: %s" % vm_attrs)
            # Attributes comparison
            result = req_args - vm_attrs
            if len(result) > 0:
                STREAM.error(" -> Section <%s> missed required attributes %s." % (vm, list(result)))
                STREAM.error(" -> This causes problems in the operation of some plugins. Check your user configuration file.")
                sys.exit()
        STREAM.success(" -> All attributes are present.")

    def check_running_state(self):
        if os.path.exists(self._PID_FILE):
            with open(self._PID_FILE, "r") as pf:
                pid = pf.readline().strip()
            proc = Popen("ps -aux|awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE)
            pids = proc.stdout.read()
            if pid in pids:
                STREAM.warning("Already running! PID: %s" % pid)
                sys.exit()
        else:
            self.create_pid()

    def create_pid(self):
        with open(self._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def args(self):
        parser = argparse.ArgumentParser('vmaker',
                                         formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50))
        parser.add_argument("-c", dest="config_path", type=str, metavar="<path>", help="specify configuration file")
        parser.add_argument("-g", dest="generate_default", action="store_true",
                            help="generate default configuration file")
        parser.add_argument("--generate-from-path", dest="generate_from_path", metavar="<path>", type=str,
                            help="generate configuration file "
                                 "with Virtual machines objects, based on names of specified directory.")
        parser.add_argument("--check-plugin", dest="check_plugin",
                            metavar="<plugin_name>", type=str, help="check target plugin")
        args = parser.parse_args()
        if args.config_path:
            self._CONFIG_FILE = args.config_path
        if args.generate_default:
            ConfigController.generate_default_config(self._CONFIG_FILE)
            exit(0)
        if args.generate_from_path:
            ConfigController.generate_from_path(args.generate_from_path)
            exit(0)
        if args.check_plugin:
            PluginController.check_plugin(args.check_plugin)
            exit(0)


if __name__ == "__main__":
    pass
