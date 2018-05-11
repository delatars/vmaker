import coloredlogs
import verboselogs

def logger_options():
    log = verboselogs.VerboseLogger(__name__)
    coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s' ,logger=log)
    return log

STREAM = logger_options()

# Some examples.
# STREAM.debug("this is a debugging message")
# STREAM.info("this is an informational message")
# STREAM.warning("this is a warning message")
# STREAM.error("this is an error message")
# STREAM.critical("this is a critical message")
