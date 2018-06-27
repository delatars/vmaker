# -*- coding: utf-8 -*-
import coloredlogs
import logging
import verboselogs
from vmaker.init.settings import LoadSettings


class _Component_filter(logging.Filter):
    """Class added additional records to logger formatter"""
    def filter(self, record):
        record.component = LoggerOptions._COMPONENT
        record.action = LoggerOptions._ACTION
        return True


class LoggerOptions:
    """Class to set up logger options"""
    _LOGFILE = LoadSettings.LOG
    DEBUG = LoadSettings.DEBUG
    _COMPONENT = "Core"
    _ACTION = ""

    @staticmethod
    def set_component(arg):
        LoggerOptions._COMPONENT = arg

    @staticmethod
    def set_action(arg=None):
        if arg is None:
            LoggerOptions._ACTION = ""
        else:
            LoggerOptions._ACTION = "[%s]" % arg

    @staticmethod
    def logger():
        """Function setting options and return logger object"""
        logfile = open(LoggerOptions._LOGFILE, "a")
        handler = logging.StreamHandler(stream=logfile)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S"))
        log = verboselogs.VerboseLogger(__name__)
        log.addFilter(_Component_filter())
        log.addHandler(handler)
        if LoggerOptions.DEBUG:
            coloredlogs.install(fmt='%(asctime)s [%(component)s] %(action)s [%(levelname)s] %(message)s', logger=log, level="debug")
        else:
            coloredlogs.install(fmt='%(asctime)s [%(component)s] %(action)s [%(levelname)s] %(message)s', logger=log)
        return log


STREAM = LoggerOptions.logger()

# Some examples.
# STREAM.debug("this is a debugging message")
# STREAM.info("this is an informational message")
# STREAM.notice("this is an informational message")
# STREAM.success("this is an informational message")
# STREAM.warning("this is a warning message")
# STREAM.error("this is an error message")
# STREAM.critical("this is a critical message")
