# -*- coding: utf-8 -*-

import os
import sys
from configparser import ConfigParser, NoSectionError
from utils.Logger import STREAM


class ConfigManager:

    def __init__(self, config_file):
        self.CONFIG_FILE = config_file

    def load_config(self):
        STREAM.info("==> Loading config...")
        config = ConfigParser()
        config.read(self.CONFIG_FILE)
        aliases, groups, vms = {}, {}, {}
        # - Generating aliases objects
        for sec in config.sections():
            try:
                if sec != "General" and config[sec]["type"] == "aliases":
                    args = {key: [val.strip() for val in value.split(",")]
                            for key, value in config.items(sec) if key != "type"}
                    if config.has_option(sec, "group"):
                        aliases[str(config[sec]["group"])] = type(str(config[sec]["group"]),
                                                                  (object, ), {"aliases": args})
                    else:
                        aliases["global"] = type("global", (object, ), {"aliases": args})
            except KeyError as wrong_key:
                STREAM.error(" -> Config Error: Wrong section <%s>! Key <%s> not specified" % (sec, wrong_key))
                STREAM.warning(" -> Section <%s> will be passed..." % sec)
        # - Generating group objects
        for sec in config.sections():
            try:
                if sec != "General" and config[sec]["type"] == "group":
                    args = {key: value for key, value in config.items(sec) if key != "type"}
                    if aliases != {}:
                        if aliases.get(sec) is None and aliases.get("global") is None:
                            # => alias null
                            groups[sec] = type(str(sec), (object, ), args)
                        elif aliases.get(sec) is not None and aliases.get("global") is not None:
                            # => alias group + global
                            groups[sec] = type(str(sec), (aliases.get(sec), aliases.get("global"), ), args)
                        elif aliases.get(sec) is not None:
                            # => alias group
                            groups[sec] = type(str(sec), (aliases.get(sec), ), args)
                        elif aliases.get("global") is not None:
                            # => alias global
                            groups[sec] = type(str(sec), (aliases.get("global"), ), args)
                    else:
                        # => alias null
                        groups[sec] = type(str(sec), (object, ), args)
            except KeyError:
                pass
        # - Generating VM objects
        for sec in config.sections():
            try:
                if sec != "General" and config[sec]["type"] == "vm":
                    args = {key: value for key, value in config.items(sec)
                            if key != "type" and key != "group" and key != "actions"}
                    act = [action.strip() for action in config[sec]["actions"].split(",")]
                    args["actions"] = act
                    if config.has_option(sec, "group") and groups.get(config[sec]["group"]) is not None:
                        vms[sec] = type(str(sec), (groups.get(config[sec]["group"]), ), args)
                    else:
                        if aliases.get("global") is None:
                            # => alias null
                            vms[sec] = type(str(sec), (), args)
                        else:
                            # => alias global
                            vms[sec] = type(str(sec), (aliases.get("global"), ), args)
            except KeyError:
                pass
        vms_work_sequence = [] 
        for sec in config.sections():
            try:
                if sec != "General" and config[sec]["type"] == "vm":
                    vms_work_sequence.append(sec)
            except KeyError:
                pass
        STREAM.success(" -> Config loaded")
        return vms, vms_work_sequence

    def load_general_config(self):
        STREAM.info("==> Loading general section...")
        if not os.path.exists(self.CONFIG_FILE):
            STREAM.critical("Config Error: Configuration file not found!\nSolutions:\n\t - Specify your configuration file by adding '-c <path>' key\n\t - Generate default configuration file by adding '-g' key\nExitting...")
            sys.exit()
        config = ConfigParser()
        config.read(self.CONFIG_FILE)
        try:
            general_config = {key: value for key, value in config.items("General")}
        except NoSectionError:
            STREAM.critical("Config Error: Section <General> does not exist!\nExitting...")
            sys.exit()
        STREAM.success(" -> General section loaded")
        return general_config

    @staticmethod
    def generate_default_config(config_file):
        template = """;Mandatory section        
[General]
; List of enabled plugins, you can create your plugin, put it to the plugins dir and enabling it here.
enabled_plugins = Vbox_start, Vbox_stop, test
; Global parameter (in minutes) to the end of which plugin process will be terminated. default=20 (mins)
;   You can specify your own "time_to_kill" parameter for each plugin.
;   Just add "time_to_kill" argument to your Plugin classobj.
time_to_kill = 20

; Specify preffered section name
[my centos]
; Mandatory keys.
; Key specifies, which type of object will be generated (vm, group, alias).
type = vm
; Key specifies plugins which will be performed for this object.
actions = Vbox_start, Vbox_stop
; Key specifies to which group this object belongs
group = linux

; User keys.
; You can specify your keys and use it in your plugin's classobj attributes. ex: self.vm_name
vm_name = ubuntu1610-amd64_ubuntu1610_1523264320143_80330
cred = root:root
ssh_port = 2020

; You can create groups and combine it with other objects.
; Groups support attribute inheritance (groups attributes have a higher priority than vm attributes)
; Specify name of the group 
[linux]
; Mandatory keys.
; Key specifies, which type of object will be generated (vm, group, alias).
type = group
"""
        with open(config_file, "w") as config:
            config.write(template)


if __name__ == "__main__":
    pass
