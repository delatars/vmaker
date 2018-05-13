# -*- coding: utf-8 -*-

import sys
import os
from subprocess import Popen, PIPE
from ConfigManager import ConfigManager
from PluginManager import PluginManager
from Logger import STREAM


class RunManager(object):

    _SESSION_FILE = '/run/vms.session'
    _PID_FILE = '/run/vms.pid'
    _CONFIG_FILE = "./actions.ini"

    def __init__(self):
        self.check_running_state()
        config = ConfigManager(self._CONFIG_FILE)
        self.general_config = config.load_general_config()
        self.config, self.config_sequence = config.load_config()
        plugins = PluginManager(self.general_config)
        self.loaded_plugins = plugins.load_plugins()

    def check_running_state(self):
        if os.path.exists(RunManager._PID_FILE):
            with open(RunManager._PID_FILE, "r") as pf:
                pid = pf.readline().strip()
            proc = Popen("ps -aux|awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE)
            pids = proc.stdout.read()
            if pid in pids:
                STREAM.warning("Already running! PID: %s" % pid)
                sys.exit()
        else:
            self.create_pid()

    def create_pid(self):        
        with open(RunManager._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def check_session(self):
        if os.path.exists(RunManager._SESSION_FILE):
            STREAM.warning("==> Detecting uncompleted session, restoring...")
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

    def parse_args(self):
        pass

if __name__ == "__main__":
    pass
