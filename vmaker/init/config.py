# -*- coding: utf-8 -*-

import os
import sys
from configparser import ConfigParser, NoSectionError
from vmaker.utils.logger import STREAM


class ConfigController:

    def __init__(self, config_file, general_config):
        self.CONFIG_FILE = config_file
        self.GENERAL_CONFIG_FILE = general_config
        if not os.path.exists(self.CONFIG_FILE):
            STREAM.critical("Config Error: Configuration file not found!\nSolutions:\n\t - Specify your configuration file by adding '-c <path>' key\n\t - Generate default configuration file by adding '-g' key\nExitting...")
            sys.exit()

    def load_config(self):
        STREAM.info("==> Loading user configuration file...")
        config = ConfigParser()
        config.read(self.CONFIG_FILE)
        aliases, groups, vms = {}, {}, {}
        # - Generating aliases objects
        STREAM.debug("==> Generating alias objects...")
        for sec in config.sections():
            STREAM.debug(" -> Loading section <%s>" % sec)
            try:
                if config[sec]["type"] == "aliases":
                    STREAM.debug("    [%s] Section seems like alias object" % sec)
                    args = {key: [val.strip() for val in value.split(",")]
                            for key, value in config.items(sec) if key != "type"}
                    STREAM.debug("    [%s] -> Section attributes: %s" % (sec, args))
                    if config.has_option(sec, "group"):
                        STREAM.debug("    [%s] -> Section have <group> attribute: assigned to group %s" % (sec, str(config[sec]["group"])))
                        aliases[str(config[sec]["group"])] = type(str(config[sec]["group"]),
                                                                  (object, ), {"aliases": args})
                        STREAM.debug("    [%s] -> Object attributes: %s" % (sec, dir(aliases[str(config[sec]["group"])])))
                    else:
                        STREAM.debug("    [%s] -> Section don't have <group> attribute: assigned to global context" % sec)
                        aliases["global"] = type("global", (object, ), {"aliases": args})
                        STREAM.debug("    [%s] -> Object attributes: %s" % (sec, dir(aliases["global"])))
                else:
                    STREAM.debug("    [%s] Section doesn't seem like alias object. Passed..." % sec)
            except KeyError as wrong_key:
                STREAM.error(" -> Config Error: Wrong section <%s>! Key <%s> not specified" % (sec, wrong_key))
                STREAM.warning(" -> Section <%s> will be passed..." % sec)
        STREAM.debug("==> Generated alias objects: %s\n" % aliases)
        # - Generating group objects
        STREAM.debug("==> Generating group objects...")
        for sec in config.sections():
            STREAM.debug(" -> Loading section <%s>" % sec)
            try:
                if config[sec]["type"] == "group":
                    STREAM.debug("    [%s] Section seems like group object" % sec)
                    args = {key: value for key, value in config.items(sec) if key != "type"}
                    STREAM.debug("    [%s] -> Section attributes: %s" % (sec, args))
                    if aliases != {}:
                        STREAM.debug("    [%s] -> Alias objects detected: object will generated with alias inheritance" % sec)
                        if aliases.get(sec) is None and aliases.get("global") is None:
                            # => alias null
                            STREAM.debug("    [%s] -> Group alias: False, Global alias: False -> object will generated without alias inheritance" % sec)
                            groups[sec] = type(str(sec), (object, ), args)
                            STREAM.debug("    [%s] -> Object attrs: %s" % (sec, groups[sec].aliases))
                        elif aliases.get(sec) is not None and aliases.get("global") is not None:
                            # => alias group + global
                            STREAM.debug("    [%s] -> Group alias: True, Global alias: True -> alias group + global alias inheritance" % sec)
                            complex_alias = dict(aliases.get(sec).aliases, **aliases.get("global").aliases)
                            aliases.get(sec).aliases = complex_alias
                            groups[sec] = type(str(sec), (aliases.get(sec), ), args)
                            STREAM.debug("    [%s] -> Object aliases: %s" % (sec, groups[sec].aliases))
                        elif aliases.get(sec) is not None:
                            # => alias group
                            STREAM.debug("    [%s] -> Group alias: True, Global alias: False -> alias group inheritance" % sec)
                            groups[sec] = type(str(sec), (aliases.get(sec), ), args)
                            STREAM.debug("    [%s] -> Object attrs: %s" % (sec, groups[sec].aliases))
                        elif aliases.get("global") is not None:
                            # => alias global
                            STREAM.debug("    [%s] -> Group alias: False, Global alias: True -> global alias inheritance" % sec)
                            groups[sec] = type(str(sec), (aliases.get("global"), ), args)
                            STREAM.debug("    [%s] -> Object attrs: %s" % (sec, groups[sec].aliases))
                    else:
                        STREAM.debug("    [%s] -> Alias objects not detected: object will generated without alias inheritance" % sec)
                        # => alias null
                        groups[sec] = type(str(sec), (object, ), args)
                else:
                    STREAM.debug("    [%s] Section doesn't seem like group object. Passed..." % sec)
            except KeyError:
                pass
        STREAM.debug("==> Generated group objects: %s\n" % groups)
        # - Generating VM objects
        STREAM.debug("==> Generating vm objects...")
        for sec in config.sections():
            STREAM.debug(" -> Loading section <%s>" % sec)
            try:
                if config[sec]["type"] == "vm":
                    STREAM.debug("    [%s] Section seems like vm object" % sec)
                    args = {key: value for key, value in config.items(sec)
                            if key != "type" and key != "group" and key != "actions"}
                    STREAM.debug("    [%s] -> Section attributes: %s" % (sec, args))
                    act = [action.strip() for action in config[sec]["actions"].split(",")]
                    args["actions"] = act
                    # alias inheritance added in group generation step
                    if config.has_option(sec, "group") and groups.get(config[sec]["group"]) is not None:
                        STREAM.debug("    [%s] Assigned group detected: inherit attributes from group <%s>" % (sec, config[sec]["group"]))
                        vms[sec] = type(str(sec), (groups.get(config[sec]["group"]), ), args)
                    else:
                        # if group doesn't exist or no group, adding alias inheritance
                        STREAM.debug("    [%s] Assigned group not detected: assign aliases" % sec)
                        if aliases.get("global") is None:
                            STREAM.debug("    [%s] Aliases not assigned: no aliases" % sec)
                            # => alias null
                            vms[sec] = type(str(sec), (), args)
                        else:
                            STREAM.debug("    [%s] Aliases assigned: global" % sec)
                            # => alias global
                            vms[sec] = type(str(sec), (aliases.get("global"), ), args)
                    retro = "    [%s] Section inheritance retrospective:"
                    final_attrs = {attr for attr in dir(vms[sec]) if not attr.startswith('__')}
                    for attr in final_attrs:
                        val = getattr(vms[sec], attr)
                        retro += "\n\t\t\t\t\t\t%s = %s" % (attr, val)
                    STREAM.debug(retro % sec)
                else:
                    STREAM.debug("    [%s] Section doesn't seem like vm object. Passed..." % sec)
            except KeyError:
                pass
        vms_work_sequence = []
        for sec in config.sections():
            try:
                if config[sec]["type"] == "vm":
                    vms_work_sequence.append(sec)
            except KeyError:
                pass
        STREAM.debug("==> Generated vm objects: %s" % vms)
        STREAM.debug("==> Generated vm objects work sequence: %s" % vms_work_sequence)
        STREAM.success(" -> Config loaded")
        return vms, vms_work_sequence

    def load_general_config(self):
        STREAM.info("==> Loading General configuration file...")
        config = ConfigParser()
        config.read(self.GENERAL_CONFIG_FILE)
        try:
            general_config = {key: value for key, value in config.items("General")}
        except NoSectionError:
            STREAM.critical("Config Error: Section <General> does not exist!\nExitting...")
            sys.exit()
        STREAM.debug("Loaded values: %s" % general_config)
        STREAM.success(" -> General section loaded")
        return general_config

    @staticmethod
    def generate_default_config(config_file):
        template = """; You can create vm objects and assign them any actions.
; Specify preffered section name.
[my centos]
; Mandatory keys.
;   Key specifies, which type of object will be created (vm, group, alias).
type = vm
;   Key specifies plugins which will be performed for this object.
actions = vbox_start, vbox_stop
;   Key specifies to which group this object belongs.
group = linux
; User keys.
;   You can specify your keys and use it in your plugin's classobj attributes. ex: self.vm_name
vm_name = ubuntu1610-amd64_ubuntu1610_1523264320143_80330
cred = root:root
ssh_port = 2020

; You can create groups and combine it with other objects.
;   Groups support attribute inheritance (groups attributes have a lower priority than vm attributes).
;   Specify name of the group.
[linux]
; Mandatory keys.
type = group
; User keys.
;actions = vbox_start, ...
;cred = root:root

; You can combine some plugins in one action, named alias.
[linux_aliases]
type = alias
; By default aliases extends to all objects, but you can assign aliases at specific group
;group = linux
common_actions = vbox_start, vbox_x_update, vbox_stop
"""
        STREAM.info("==> Generating default configuration file...")
        if os.path.exists(config_file):
            STREAM.warning(" -> File %s already exists!" % config_file)
            STREAM.warning(" -> Do you want to overwrite it? (y/n): ")
            answers = ["y", "n"]
            while 1:
                choice = raw_input().lower()
                if choice in answers:
                    break
                STREAM.error("Choose y or n! : ")
            if choice == answers[0]:
                with open(config_file, "w") as config:
                    config.write(template)
                STREAM.success(" -> Generated %s" % config_file)
            else:
                STREAM.notice(" -> Cancelled by user.")
                sys.exit()
        else:
            with open(config_file, "w") as config:
                config.write(template)
            STREAM.success(" -> Generated %s" % config_file)


if __name__ == "__main__":
    pass
