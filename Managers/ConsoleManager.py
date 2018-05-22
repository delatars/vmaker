# -*- coding: utf-8 -*-

import optparse
from RunManager import RunManager
from ConfigManager import ConfigManager


class ConsoleManager:

    def __init__(self):
        self.args()

    def args(self):
        parser = optparse.OptionParser('Engine.py [options]\n\nOptions:\n  -c  - Specify config file\n  -g  - Generate default config\n  -i  - Enabling interactive mode, affects to print to stdout\n\nAdditional options:\n\t--debug Enabling debug prints')
        parser.add_option("-c", dest="config_path", type="string", help="Specify config file location")
        parser.add_option("-g", dest="generate_default", type="string", help="Generate default config")
        options, args = parser.parse_args()
        # defaults

        if options.config_path:
            RunManager._CONFIG_FILE = options.config_path
        if options.generate_default:
            ConfigManager.generate_default_config()
            exit(0)
