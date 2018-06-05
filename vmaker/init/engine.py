# -*- coding: utf-8 -*-

import sys
import os
import optparse
from subprocess import Popen, PIPE
from vmaker.init.config import ConfigController
from vmaker.init.plugins import PluginController
from vmaker.init.settings import vars
from vmaker.utils.logger import STREAM


class Engine(object):
    _SESSION_FILE = vars.SESSION_FILE
    _PID_FILE = vars.PID_FILE
    _GENERAL_CONFIG = vars.GENERAL_CONFIG
    _CONFIG_FILE = vars.CONFIG_FILE

    def __init__(self):
        self.check_running_state()
        self.args()
        config = ConfigController(self._CONFIG_FILE, self._GENERAL_CONFIG)
        self.general_config = config.load_general_config()
        self.config, self.config_sequence = config.load_config()
        plugins = PluginController(self.general_config)
        self.loaded_plugins = plugins.load_plugins()

    def check_running_state(self):
        if os.path.exists(self._PID_FILE):
            with open(self._PID_FILE, "r") as pf:
                pid = pf.readline().strip()
            proc = Popen("ps -aux|awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE)
            pids = proc.stdout.read()
            if pid in pids:
                STREAM.warning("Already running! PID: %s" % pid)
                sys.exit()
        else:
            self.create_pid()

    def create_pid(self):
        STREAM.debug("==> Creating pid file: %s" % self._PID_FILE)
        with open(self._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def check_session(self):
        if os.path.exists(self._SESSION_FILE):
            STREAM.warning("==> Detecting uncompleted session, restoring...")
            with open(self._SESSION_FILE, "r") as sf:
                vms = sf.readlines()
            STREAM.debug("vms: %s" % vms)
            last_vm_name, last_modified_vm_snapshot = vms.pop(-1).split("<--->")
            STREAM.debug("Taken snapshot: %s" % last_modified_vm_snapshot)
            ready_vms = [vm.split(" - ")[0].strip() for vm in vms]
            STREAM.debug("Ready vms: %s" % ready_vms)
            map(lambda x: self.config_sequence.remove(x), ready_vms)
            return last_modified_vm_snapshot.strip(), last_vm_name.strip()
        return None

    def update_session(self, vm_name, snapshot="None"):
        with open(self._SESSION_FILE, "a") as sf:
            sf.write("%s <---> %s\n" % (vm_name, snapshot))

    def destroy_session(self):
        os.remove(self._SESSION_FILE)

    def args(self):
        parser = optparse.OptionParser('vmaker [options]\n\nOptions:\n  -c <path>  - Specify config file\n  -g         - Generate default config\n\n  --gfp <path>  - Generate config, based on specified path')
        parser.add_option("-c", dest="config_path", type="string", help="Specify config file location")
        parser.add_option("-g", dest="generate_default", action="store_true", help="Generate default config")
        parser.add_option("--gfp", dest="generate_from_path", type="string", help="Generate config from path")
        options, args = parser.parse_args()
        # defaults

        if options.config_path:
            self._CONFIG_FILE = options.config_path
        if options.generate_default:
            ConfigController.generate_default_config(self._CONFIG_FILE)
            exit(0)
        if options.generate_from_path:
            ConfigController.generate_from_path(options.super_generate)
            exit(0)


if __name__ == "__main__":
    pass
