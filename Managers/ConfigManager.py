# -*- coding: utf-8 -*-

import os
import sys
from configparser import ConfigParser, NoSectionError
from Logger import STREAM


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
        if not os.path.exists(self.CONFIG_FILE):
            STREAM.critical("Config Error: Actions.ini not found! You may generate it by add -g key.\nExitting...")
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
    
    def generate_default_config(self):
        config = ConfigParser()
        # cmd = Popen("vboxmanage list vms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        # vms = cmd.stdout.read()
        # vms = vms.strip().replace('"', "").split("\n")
        # for vm in vms:
        #     config[vm] = {"actions": "keyword1, keyword2, keyword3..."}
        # cfg = open("actions.ini", "w")
        # config.write(cfg)
        # cfg.close()

if __name__ == "__main__":
    pass
