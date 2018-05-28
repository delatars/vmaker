# -*- coding: utf-8 -*-
import coloredlogs
import logging
import verboselogs
from configparser import ConfigParser
from vmaker.init.settings import vars


class Component_filter(logging.Filter):
    def filter(self, record):
        record.component = LoggerOptions.COMPONENT
        return True


class LoggerOptions:
    _LOGFILE = "./stdout.log"
    DEBUG = False
    COMPONENT = "Engine"

    def __init__(self):
        vars()
        config = ConfigParser()
        config.read(vars.GENERAL_CONFIG)
        debug = config["General"]["debug"]
        if debug.lower() == "true":
            self.DEBUG = True
        self._LOGFILE = config["General"]["log"]

    def logger(self):
        logfile = open(self._LOGFILE, "a")
        handler = logging.StreamHandler(stream=logfile)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S"))
        log = verboselogs.VerboseLogger(__name__)
        log.addFilter(Component_filter())
        log.addHandler(handler)
        if self.DEBUG:
            coloredlogs.install(fmt='%(asctime)s [%(component)s] [%(levelname)s] %(message)s', logger=log, level="debug")
        else:
            coloredlogs.install(fmt='%(asctime)s [%(component)s] [%(levelname)s] %(message)s', logger=log)
        return log


STREAM = LoggerOptions().logger()

# Some examples.
# STREAM.debug("this is a debugging message")
# STREAM.info("this is an informational message")
# STREAM.success("this is an informational message")
# STREAM.warning("this is a warning message")
# STREAM.error("this is an error message")
# STREAM.critical("this is a critical message")
