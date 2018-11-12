# -*- coding: utf-8 -*-

import os
import sys
from configparser import ConfigParser
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM


class ConfigController:
    """ Class works with configuration files
        - Loads general configuration file options
        - Creates vm/group/alias objects based on user configuration file
        - Generates default user configuration file """

    def __init__(self, config_file):
        self.CONFIG_FILE = config_file
        if not os.path.exists(self.CONFIG_FILE):
            STREAM.critical("Config Error: Configuration file not found!\nSolutions:\n\t - Specify your configuration file by adding '-c <path>' key\n\t - Generate default configuration file by adding '-g' key\nExitting...")
            sys.exit()

    def load_config(self):
        STREAM.info("==> Loading user configuration file...")
        config = ConfigParser()
        config.read(self.CONFIG_FILE)
        aliases, groups, vms, cmds = {}, {}, {}, {}
        # - Generating aliases objects
        STREAM.debug("==> Generating alias objects...")
        for sec in config.sections():
            STREAM.debug(" -> Loading section '%s'" % sec)
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
                STREAM.error(" -> Config Error: Wrong section '%s' Key %s not specified" % (sec, wrong_key))
                sys.exit()
        STREAM.debug("[*] ==> Generated alias objects: %s\n" % aliases)
        # - Generating group objects
        STREAM.debug("==> Generating group objects...")
        for sec in config.sections():
            STREAM.debug(" -> Loading section '%s'" % sec)
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
            except KeyError as wrong_key:
                STREAM.error(" -> Config Error: Wrong section '%s' Key '%s' not specified" % (sec, wrong_key))
                sys.exit()
        STREAM.debug("[*] ==> Generated group objects: %s\n" % groups)
        # - Generating VM objects
        STREAM.debug("==> Generating vm objects...")
        vms_work_sequence = []
        for sec in config.sections():
            STREAM.debug(" -> Loading section '%s'" % sec)
            try:
                if config[sec]["type"] == "vm":
                    STREAM.debug("    [%s] Section seems like vm object" % sec)
                    args = {key: value for key, value in config.items(sec)
                            if key != "type" and key != "group" and key != "actions"}
                    STREAM.debug("    [%s] -> Section attributes: %s" % (sec, args))
                    # firstly check if vm section exists action attr
                    # then below check maybe it inherit from group
                    try:
                        act = config[sec]["actions"]
                        args["actions"] = act
                    except KeyError:
                        pass
                    # alias inheritance added in group generation step
                    if config.has_option(sec, "group") and groups.get(config[sec]["group"]) is not None:
                        STREAM.debug("    [%s] Assigned group detected: inherit attributes "
                                     "from group '%s'" % (sec, config[sec]["group"]))
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
                    # Check if 'action' attr was inherited from group
                    try:
                        acts = getattr(vms[sec], "actions")
                        setattr(vms[sec], "actions", [action.strip() for action in acts.split(",")])
                        retro = "    [%s] Section inheritance retrospective:"
                        final_attrs = {attr for attr in dir(vms[sec]) if not attr.startswith('__')}
                        for attr in final_attrs:
                            val = getattr(vms[sec], attr)
                            retro += "\n\t\t\t\t\t\t%s = %s" % (attr, val)
                        STREAM.debug(retro % sec)
                        vms_work_sequence.append(sec)
                    except AttributeError as wrong_key:
                        STREAM.error(" -> Config Error: Wrong section '%s'"
                                     " Key %s not specified" % (sec, str(wrong_key).split(" ")[-1]))
                        del vms[sec]
                        sys.exit()
                else:
                    STREAM.debug("    [%s] Section doesn't seem like vm object. Passed..." % sec)
            except KeyError as wrong_key:
                STREAM.error(" -> Config Error: Wrong section '%s' Key '%s' not specified" % (sec, wrong_key))
                sys.exit()
        STREAM.debug("[*] ==> Generated vm objects: %s" % vms)
        STREAM.debug("[*] ==> Generated vm objects work sequence: %s" % vms_work_sequence)
        STREAM.debug("==> Finding sections with execution...")
        for sec in config.sections():
            try:
                if config[sec]["type"] == "execution":
                    STREAM.debug(" -> Found section '%s'" % sec)
                    args = {key: value for key, value in config.items(sec) if key != "type"}
                    cmds = dict(cmds, **args)
            except KeyError as wrong_key:
                STREAM.error(" -> Config Error: Wrong section '%s' Key '%s' not specified" % (sec, wrong_key))
                sys.exit()
        STREAM.debug("[*] ==> Found execution aliases: %s" % cmds)
        STREAM.success(" -> User configuration file loaded")
        return vms, vms_work_sequence, cmds

    @staticmethod
    def generate_from_path(path):
        """ Generating config based on path to Virtual box """

        cfg = os.path.join(LoadSettings.WORK_DIR, "generated.ini")
        config = ConfigParser()
        config.read(cfg)
        for vm in os.listdir(path):
            if os.path.isdir(os.path.join(path, vm)):
                config.add_section(vm)
                config.set(vm, "type", "vm")
                config.set(vm, "vm_name", vm)
        with open(cfg, "w") as conf:
            config.write(conf)
        STREAM.success("Generated %s" % cfg)

    @staticmethod
    def generate_default_config(config_file):
        template = """; You can create vm objects and assign them any actions.
; Specify preffered section name.
[debian9-x86-template]
; Mandatory keys.
;   Key specifies, which type of object will be created (vm, group, alias).
type = vm
;   Key specifies Keywords which will be performed for this VirtualMachine
actions = port_forwarding, vbox_start, execute_command, vbox_stop, create_base_snapshot
; Variable keys
;   Key specifies to which group this object belongs.
group = linux
; You may specify email to receive notifications about Keyword's errors.
;alert = user@mail.ru
; That description will be shown in subject of the email
;alert_description = install curl in vm
; Attributes needed for the correct work of a Keyword's
; name of the virtual machine in VirtualBox.
vm_name = debian9-x86-template
; Command which will be executed in VirtualMachine by Keyword "execute_command"
execute_command = apt-get install -y clamav

[fedora27-amd64]
type = vm
; actions will be inherited from group
group = linux
vm_name = fedora27-amd64
execute_command = dnf install -y clamav
 
[freebsd10-amd64]
type = vm
group = linux
vm_name = freebsd10-amd64
execute_command = pkg install -y clamav

; You can create groups and combine it with other objects.
;   Groups support attribute inheritance (groups attributes have a lower priority than vm attributes).
;   Specify name of the group.
[linux]
; Mandatory key.
type = group
;   Key specifies keywords which will be performed for the group of VirtualMachines.
actions = port_forwarding, vbox_start, execute_command, vbox_stop
; You can specify a timeout for each Keyword after which the process will be terminated (ex: <Keyword_name>_timeout)
execute_command_timeout = 10

; You can combine some Keywords in one action, named alias.
[linux_aliases]
type = alias
; By default aliases extends to all objects, but you can assign aliases at specific group
;group = linux
reboot = vbox_stop, vbox_start
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
