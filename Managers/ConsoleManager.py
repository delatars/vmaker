# -*- coding: utf-8 -*-

import optparse
from RunManager import RunManager
from ConfigManager import ConfigManager
from utils.Logger import LoggerOptions


class ConsoleManager:

    def __init__(self):
        self.args()

    def args(self):
        parser = optparse.OptionParser('\n\t--test <test type> --from <mail from> --to <mail to>\n\nAdditional arguments:\n\t--server Specify server address (default=127.0.0.1:25)')
        parser.add_option("-c", dest="config_path", type="string", help="Specify config file location")
        parser.add_option("-g", dest="generate_default", type="string", help="Generate default config")
        parser.add_option("-i", dest="interactive", help="Enabling interactive mode, affects to print to stdout")
        parser.add_option("--debug", dest="debug", type="string", help="Enabling debug prints")
        options, args = parser.parse_args()

        if options.config_path:
            RunManager._CONFIG_FILE = options.config_path
        if options.generate_default:
            ConfigManager.generate_default_config()
            exit(0)
        if options.interactive:
            LoggerOptions.INTERACTIVE = True
        if options.debug:
            LoggerOptions.DEBUG = True

