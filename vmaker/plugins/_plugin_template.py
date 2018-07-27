# -*- coding: utf-8 -*-
#
# This module represents how plugins should be created.
#
#
# Plugins must direct output to main logger handler.
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
# Each plugin is launched in child process, and therefore you will not see the exceptions of the plugin.
# This wrap function allows to intercept exceptions in child processes and redirect it to logger handler.
from vmaker.utils.auxilary import exception_interceptor


# In the plugin's module should only be one class, named Keyword
class Keyword:
    """This class represents the plugin's template"""
    # Plugins can take attributes from user configuration file.
    # default.ini:
    # ...
    # [linux]
    # type = vm
    # actions = test
    # info = Hello
    # ...
    #  class Keyword(object):
    #      def main(self):
    #          print self.info
    # ########################
    #
    # REQUIRED_CONFIG_ATTRS - mandatory attribute
    # List of mandatory arguments taken from the user configuration file necessary for the correct work of the plugin.
    REQUIRED_CONFIG_ATTRS = ["info"]

    # wrap function to intercept exceptions.
    @exception_interceptor
    # Mandatory method which represents an entrypoint of the plugin.
    def main(self):
        STREAM.info("plugin's start.")
        # Attribute which automatically taken from the user configuration file.
        # self.info = self.info
        # ...
        # ...
        # plugin's method call
        # self.print_info()

    # plugin's methods
    # ...
    # def print_info(self):
    #     STREAM.info("Config attribute: %s " % str(self.info))
    #
    # ...
    # ...


if __name__ == "__main__":
    pass
