# -*- coding: utf-8 -*-

import importlib
import sys
from time import sleep
from Logger import STREAM


class PluginManager:
    
    def __init__(self, gen_config):
        self.general_config = gen_config

    def load_plugins(self):
        lst_of_plugins = [plug.strip() for plug in self.general_config["enabled_plugins"].split(",")]
        STREAM.info("...................................................................")
        STREAM.info("==> Checking plugins...")
        for plugin in lst_of_plugins:
            self.check_plugin(plugin)
        loaded_plugins = {}
        STREAM.info("==> Loading plugins...")
        for plugin in lst_of_plugins:
            loaded_plugins[plugin] = self.load_plugin(plugin)
        return loaded_plugins

    def load_plugin(self, plugin_name):        
        plugin = importlib.import_module("Plugins.%s" % plugin_name)
        cls = getattr(plugin, "Keyword")
        STREAM.info(" -> Loading plugin <%s>..........OK" % plugin_name)
        sleep(0.5)
        return cls        

    def check_plugin(self, plugin_name):        
        try:
            plugin = importlib.import_module("Plugins.%s" % plugin_name)
            cls = getattr(plugin, "Keyword")
            entrypoint = getattr(cls, "main")
            STREAM.info(" -> Checking plugin <%s>.........OK" % plugin_name)
        except ImportError as err:
            STREAM.warning(" -> Checking plugin <%s>.........FAILED" % plugin_name)
            STREAM.critical("  -> %s" % err)
            sys.exit()
        except AttributeError as err:
            STREAM.warning(" -> Checking plugin <%s>.........FAILED" % plugin_name)
            STREAM.critical("  -> %s" % err)
            sys.exit
        sleep(0.5)
