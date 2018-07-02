# -*- coding: utf-8 -*-

import importlib
import sys
from time import sleep
from vmaker.utils.logger import STREAM


class PluginController:
    """Class controls loading plugins
        - Check plugins
        - Load plugins"""
    
    def __init__(self, plugins):
        self.enabled_plugins = plugins

    def load_plugins(self):
        lst_of_plugins = self.enabled_plugins
        STREAM.info("==> Checking plugins...")
        for plugin in lst_of_plugins:
            PluginController.check_plugin(plugin)
        loaded_plugins = {}
        STREAM.info("==> Loading plugins...")
        for plugin in lst_of_plugins:
            loaded_plugins[plugin] = self.load_plugin(plugin)
        return loaded_plugins

    def load_plugin(self, plugin_name):        
        plugin = importlib.import_module("vmaker.plugins.%s" % plugin_name)
        cls = getattr(plugin, "Keyword")
        STREAM.success(" -> Loading plugin <%s>..........OK" % plugin_name)
        sleep(0.1)
        return cls        

    @staticmethod
    def check_plugin(plugin_name):
        try:
            STREAM.debug(" -> Check for plugin:")
            plugin = importlib.import_module("vmaker.plugins.%s" % plugin_name)
            STREAM.debug("    %s" % plugin)
            STREAM.debug(" -> Check for a class <Keyword>:")
            cls = getattr(plugin, "Keyword")
            STREAM.debug("    %s" % cls)
            STREAM.debug(" -> Check for entrypoint <main>:")
            entry = getattr(cls, "main")
            STREAM.debug("    %s" % entry)
            STREAM.debug(" -> Check for REQUIRED_CONFIG_ATTRS:")
            entry = getattr(cls, "REQUIRED_CONFIG_ATTRS")
            STREAM.debug("    %s" % entry)
            STREAM.success(" -> Checking plugin <%s>.........OK" % plugin_name)
        except ImportError as err:
            STREAM.warning(" -> Checking plugin <%s>.........FAILED" % plugin_name)
            STREAM.critical("  -> %s" % err)
            sys.exit()
        except AttributeError as err:
            STREAM.warning(" -> Checking plugin <%s>.........FAILED" % plugin_name)
            STREAM.critical("  -> %s" % err)
            sys.exit()
        finally:
            sleep(0.1)

if __name__ == "__main__":
    pass
