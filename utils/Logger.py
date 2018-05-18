import coloredlogs
import verboselogs


class LoggerOptions:
    INTERACTIVE = False
    DEBUG = False

    @staticmethod
    def logger():
        logfile = open("out.log", "a")
        log = verboselogs.VerboseLogger(__name__)
        if LoggerOptions.DEBUG:
            coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', logger=log, level="debug")
            return log
        coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', logger=log, stream=logfile)
        return log


STREAM = LoggerOptions.logger()

# Some examples.
# STREAM.debug("this is a debugging message")
# STREAM.info("this is an informational message")
# STREAM.warning("this is a warning message")
# STREAM.error("this is an error message")
# STREAM.critical("this is a critical message")
