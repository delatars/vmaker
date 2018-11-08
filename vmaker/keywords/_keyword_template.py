# -*- coding: utf-8 -*-
#
# This module represents how keywords should be created.
#
#
# Keywords must direct output to main logger handler.
# You must use STREAM for any output info.
#
from vmaker.utils.logger import STREAM
#
# Some examples.
# STREAM.debug("this is a debugging message")
# STREAM.info("this is an informational message")
# STREAM.notice("this is an informational message")
# STREAM.success("this is an informational message")
# STREAM.warning("this is a warning message")
# STREAM.error("this is an error message")
# STREAM.critical("this is a critical message")
#
# Each keyword is launched in child process, and therefore you will not see the exceptions of the keyword.
# This wrap function allows to intercept exceptions in child processes and redirect it to logger handler.
from vmaker.utils.auxilary import exception_interceptor


# In the keyword's module should only be one class, named Keyword
class Keyword:
    """ This class represents the keyword's template """
    # Keywords can take attributes from user configuration file.
    # default.ini:
    # ...
    # [linux]
    # type = vm
    # actions = test
    # info = Hello
    # ...
    #
    # keywords/test.py
    #  ...
    #  class Keyword(object):
    #      def main(self):
    #          print self.info
    #  ...
    # Output will be:
    # >>> Hello
    # ########################
    #
    # REQUIRED_CONFIG_ATTRS - mandatory attribute
    # List of mandatory arguments taken from the user configuration file necessary for the correct work of the keyword.
    REQUIRED_CONFIG_ATTRS = ["info"]

    # Wrap function to intercept exceptions in child proccesses.
    @exception_interceptor
    def main(self):
        """ Mandatory method, invoked by vmaker Core process, which represents an entrypoint of the keyword. """
        STREAM.info("keyword's start.")
        # Attribute which automatically taken from the user configuration file.
        # self.info = self.info
        # ...
        # ...
        # keyword's method call
        # self.print_info()

    # keyword's methods
    # ...
    # def print_info(self):
    #     STREAM.info("Config attribute: %s " % str(self.info))
    #
    # ...
    # ...

    def clearing(self):
        """ This method, invoked by vmaker Core process, if keyword was interrupted or complete unsuccessfully.
            If this method is not implemented, doing nothing. """
        print "Clear actions"


if __name__ == "__main__":
    pass
