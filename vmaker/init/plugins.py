# -*- coding: utf-8 -*-

import importlib
import sys
from time import sleep
from vmaker.utils.logger import STREAM


class PluginController:
    """ Class controls loading plugins
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
        STREAM.success(_aligner(" -> Loading plugin <%s>" % plugin_name, "OK"))
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
            STREAM.success(_aligner(" -> Checking plugin <%s>" % plugin_name, "OK"))
        except ImportError as err:
            STREAM.warning(_aligner(" -> Checking plugin <%s>" % plugin_name, "FAILED"))
            STREAM.critical("  -> %s" % err)
            sys.exit()
        except AttributeError as err:
            STREAM.warning(_aligner(" -> Checking plugin <%s>" % plugin_name, "FAILED"))
            STREAM.critical("  -> %s" % err)
            sys.exit()
        finally:
            sleep(0.1)


def _aligner(line, status):
    line_width = 60
    length = len(line)
    if length > line_width:
        return line + status
    add = line_width - length
    return line + "."*add + status


if __name__ == "__main__":
    pass
