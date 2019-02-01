# -*- coding: utf-8 -*-
import sys
import argparse
from vmaker.init.config import ConfigController
from vmaker.init.keywords import KeywordController
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM


class Engine(object):
    """ Class controls prerun of the program
        - Parse command-line arguments
        - Execute config module
        - Execute keywords module
        """
    _SESSION_FILE = LoadSettings.SESSION_FILE
    _GENERAL_CONFIG = LoadSettings.GENERAL_CONFIG
    _CONFIG_FILE = LoadSettings.CONFIG_FILE_PATH

    def __init__(self):
        # Parse command-line arguments.
        self.args()
        config = ConfigController(self._CONFIG_FILE)
        # Load user configuration file and sequence to move on.
        self.config, self.config_sequence, self.executions = config.load_config()
        # Check and load keywords.
        self.loaded_keywords = KeywordController(LoadSettings.ENABLED_KEYWORDS).load_keywords()
        self.check_attributes_dependencies()

    def check_attributes_dependencies(self):
        STREAM.info("==> Checking for keywords required attributes.")
        for vm in self.config_sequence:
            # Set of required attributes for all Keywords used in the VirtualMachine
            req_args = set()
            STREAM.debug("==> VirtualMachine: %s" % vm)
            for action in self.config[vm].actions:
                try:
                    # List of required attributes for the Keyword to work
                    req_attr = self.loaded_keywords[action].REQUIRED_CONFIG_ATTRS
                    # Add required attributes of current action to summary set
                    req_args = set(req_args) | set(req_attr)
                except KeyError:
                    # If action not in executions section, check for aliases
                    if action not in self.executions.keys():
                        # Check aliases actions for required attributes
                        try:
                            aliases = self.config[vm].aliases[action]
                        # Intercept if VirtualMachine have no aliases
                        except KeyError as key:
                            STREAM.error("The keyword (%s) you use in the configuration file does not exist or is not enabled." % key)
                            STREAM.warning("You can't use this keyword until you turn it on in .vmaker.ini")
                            sys.exit(1)
                        # Intercept if VirtualMachine have no aliases
                        except AttributeError:
                            STREAM.error("The keyword (u'%s') you use in the configuration file does not exist or is not enabled." % action)
                            STREAM.warning("You can't use this keyword until you turn it on in .vmaker.ini")
                            sys.exit(1)
                        for act in aliases:
                            req_attr = self.loaded_keywords[act].REQUIRED_CONFIG_ATTRS
                            req_args = set(req_args) | set(req_attr)
            vm_attrs = [name for name in dir(self.config[vm]) if not name.startswith('__')]
            req_args = set(req_args)
            vm_attrs = set(vm_attrs)
            STREAM.debug(" -> [%s] Required attributes for actions: %s" % (vm, req_args))
            STREAM.debug(" -> [%s] VirtualMachines attributes: %s" % (vm, vm_attrs))
            # Attributes comparison
            result = req_args - vm_attrs
            if len(result) > 0:
                STREAM.error(" -> Section <%s> missed required attributes %s." % (vm, list(result)))
                STREAM.error(" -> This causes problems in the operation of some keywords. Check your user configuration file.")
                sys.exit()
        STREAM.success(" -> All attributes are present.")

    def args(self):
        parser = argparse.ArgumentParser('vmaker',
                                         formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50))
        parser.add_argument("-c", dest="config_path", type=str, metavar="<path>", help="specify configuration file to use")
        parser.add_argument("-g", dest="generate_default", action="store_true",
                            help="generate default configuration file")
        parser.add_argument("--generate-from-path", dest="generate_from_path", metavar="<path>", type=str,
                            help="generate configuration file "
                                 "with Virtual machines objects, based on names of specified directory.")
        parser.add_argument("--check-keyword", dest="check_keyword",
                            metavar="<keyword_name>", type=str, help="check target keyword")
        args = parser.parse_args()
        if args.config_path:
            self._CONFIG_FILE = args.config_path
        if args.generate_default:
            ConfigController.generate_default_config(self._CONFIG_FILE)
            exit(0)
        if args.generate_from_path:
            ConfigController.generate_from_path(args.generate_from_path)
            exit(0)
        if args.check_keyword:
            KeywordController.check_keyword(args.check_keyword)
            exit(0)


if __name__ == "__main__":
    pass
