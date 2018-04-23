# -*- coding: utf-8 -*-
import sys
import os
import importlib
from subprocess import Popen, PIPE
from datetime import datetime
from configparser import ConfigParser
from auxilary import Fabric


class RunManager(object):
    _SESSION_FILE = '/run/vms.session'
    _PID_FILE = '/run/vms.pid'

    def __init__(self):
        self.check_running_state()
        self.config, self.config_sequence = self.load_config()

    def check_running_state(self):
        if os.path.exists(RunManager._PID_FILE):
            with open(RunManager._PID_FILE, "r") as pf:
                pid = pf.readline().strip()
            proc = Popen("ps -aux|awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE)
            pids = proc.stdout.read()
            if pid in pids:
                print "Already running! PID: %s" % pid
                sys.exit()
        else:
            self.create_pid()

    def create_pid(self):        
        with open(RunManager._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def check_session(self):
        if os.path.exists(RunManager._SESSION_FILE):
            print "==> Detecting uncompleted session, restoring..."
            with open(RunManager._SESSION_FILE, "r") as sf:
                vms = sf.readlines()
            last_modified_vm_snapshot = vms.pop(-1)[1].strip()
            ready_vms = [vm.split(" - ")[0].strip() for vm in vms]
            map(lambda x: self.config_sequence.remove(x), ready_vms)
            return last_modified_vm_snapshot
        return None

    def update_session(self, vm, snapshot):
        with open(RunManager._SESSION_FILE, "a") as sf:
            sf.write("%s - %s\n" % (vm, snapshot))

    def destroy_session(self):
        os.remove(RunManager._SESSION_FILE)

    def load_config(self):
        if not os.path.exists('actions.ini'):
            print "Actions.ini not found! You may generate it by add -g key."
            sys.exit()
        config = ConfigParser()
        config.read("actions.ini")
        aliases, groups, vms = {}, {}, {}
        # - Generating aliases objects
        for sec in config.sections():
            try:
                if config[sec]["type"] == "aliases":
                    args = {key: [val.strip() for val in value.split(",")]
                            for key, value in config.items(sec) if key != "type"}
                    if config.has_option(sec, "group"):
                        aliases[str(config[sec]["group"])] = type(str(config[sec]["group"]),
                                                                  (object, ), {"aliases": args})
                    else:
                        aliases["global"] = type("global", (object, ), {"aliases": args})
            except KeyError as wrong_key:
                print "Wrong section <%s>! Key <%s> not specified, passed..." % (sec, wrong_key)
        # - Generating group objects
        for sec in config.sections():
            try:
                if config[sec]["type"] == "group":
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
            except KeyError as wrong_key:
                print "Wrong section <%s>! Key <%s> not specified, passed..." % (sec, wrong_key)
        # - Generating VM objects
        for sec in config.sections():
            try:
                if config[sec]["type"] == "vm":
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
            except KeyError as wrong_key:
                print "Wrong section <%s>! Key <%s> not specified, passed..." % (sec, wrong_key)
        vms_work_sequence = [sec for sec in config.sections() if config[sec]["type"] == "vm"]
        return vms, vms_work_sequence

    @staticmethod
    def generate_default_config():
        config = ConfigParser()
        cmd = Popen("vboxmanage list vms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        vms = cmd.stdout.read()
        vms = vms.strip().replace('"', "").split("\n")
        for vm in vms:
            config[vm] = {"actions": "keyword1, keyword2, keyword3..."}
        cfg = open("actions.ini", "w")
        config.write(cfg)
        cfg.close()


class Core(RunManager):

    def __init__(self):
        super(Core, self).__init__()
        self.current_vm = None
        self.current_vm_snapshot = self.check_session()
        if self.current_vm_snapshot is not None:
            self.restore_from_snapshot()
        self.plugins_module = None
        self.main()
    
    def main(self):
        for vm in self.config_sequence:
            self.current_vm = self.config[vm]
            print ">>>>> Initialize %s <<<<<" % self.current_vm.__name__
            # self.take_snapshot(self.current_vm.name)
            Fabric.obj = self.current_vm
            self.plugins_module = importlib.import_module("Plugins")
            self.do_actions(self.current_vm.actions)

    # recursion function
    def do_actions(self, actions_list):
        def _restore(exception):
            print "! ==> Exception in vm <%s>:" % self.current_vm.__name__
            print "! - %s" % exception
            print "! - Can't proceed with this vm"
            # self.restore_from_snapshot(self.current_vm.name)
            print "! - Restore complete, going next..."

        for action in actions_list:
            try:
                keyword = getattr(self.plugins_module, "Keyword_"+action)
                try:
                    keyword().main()
                except Exception as exc:
                    _restore(exc)
                    break
            except AttributeError:
                try:
                    self.do_actions(self.current_vm.aliases[action])
                except KeyError as exc:
                    exc = "Unknown action! " + str(exc)
                    _restore(exc)
                    break

    def take_snapshot(self, vm_name):
        print("==> Taking a snapshot")
        self.current_vm_snapshot = vm_name+"__"+str(datetime.now())[:-7].replace(" ", "_")
        Popen('VBoxManage snapshot %s take %s' % (vm_name, self.current_vm_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        self.update_session(self.current_vm.__name__, self.current_vm_snapshot)

    def restore_from_snapshot(self):
        print "! - Restoring to previous state..."
        Popen('VBoxManage snapshot restore %s' % (self.current_vm_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()

upd = Core()
