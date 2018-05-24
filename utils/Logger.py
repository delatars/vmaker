import coloredlogs
import logging
import verboselogs


class LoggerOptions:
    _LOGFILE = "stdout.log"
    DEBUG = True

    @staticmethod
    def logger():
        logfile = open(LoggerOptions._LOGFILE, "a")
        handler = logging.StreamHandler(stream=logfile)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S"))
        log = verboselogs.VerboseLogger(__name__)
        log.addHandler(handler)
        if LoggerOptions.DEBUG:
            coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', logger=log, level="debug")
        else:
            coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', logger=log)
        return log


STREAM = LoggerOptions.logger()

# Some examples.
# STREAM.debug("this is a debugging message")
# STREAM.info("this is an informational message")
# STREAM.success("this is an informational message")
# STREAM.warning("this is a warning message")
# STREAM.error("this is an error message")
# STREAM.critical("this is a critical message")
