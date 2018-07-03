# -*- coding: utf-8 -*-

import sys
import os
import optparse
import hashlib
from subprocess import Popen, PIPE
from vmaker.init.config import ConfigController
from vmaker.init.plugins import PluginController
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM


class Engine(object):
    """Class controls prerun of the program
        - Parse command-line arguments
        - Execute config module
        - Execute plugins module
        - Creating PID file
        - Creating Session file
        - Control session
        """
    _SESSION_FILE = LoadSettings.SESSION_FILE
    _PID_FILE = LoadSettings.PID_FILE
    _GENERAL_CONFIG = LoadSettings.GENERAL_CONFIG
    _CONFIG_FILE = LoadSettings.CONFIG_FILE_PATH

    def __init__(self):
        # Check if one instance of the program is already running.
        self.check_running_state()
        # Parse command-line arguments.
        self.args()
        config = ConfigController(self._CONFIG_FILE)
        # Load user configuration file and sequence to move on.
        self.config, self.config_sequence = config.load_config()
        # Check and load plugins.
        self.loaded_plugins = PluginController(LoadSettings.ENABLED_PLUGINS).load_plugins()
        self.check_attributes_dependencies()

    def check_attributes_dependencies(self):
        STREAM.info("==> Checking for plugins required attributes.")
        for vm in self.config_sequence:
            req_args = []
            for action in self.config[vm].actions:
                try:
                    req_attr = self.loaded_plugins[action].REQUIRED_CONFIG_ATTRS
                except KeyError as key:
                    STREAM.error("Plugin %s not enabled." % key)
                    STREAM.warning("You can't use this plugin until you turn it on in .vmaker.ini")
                    sys.exit()
                for attr in req_attr:
                    req_args.append(attr)
            vm_attrs = [name for name in dir(self.config[vm]) if not name.startswith('__')]
            req_args = set(req_args)
            vm_attrs = set(vm_attrs)
            result = req_args - vm_attrs
            if len(result) > 0:
                STREAM.error(" -> Section <%s> missed required attributes %s." % (vm, list(result)))
                STREAM.error(" -> This causes problems in the operation of some plugins. Check your user configuration file.")
                sys.exit()
        STREAM.success(" -> All attributes are present.")

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
        with open(self._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def check_session(self):
        if os.path.exists(self._SESSION_FILE):
            STREAM.warning("==> Detecting uncompleted session, restoring...")
            with open(self._SESSION_FILE, "r") as sf:
                vms = sf.readlines()
            checksum = vms.pop(0).strip()
            if checksum != self.get_hash(self._CONFIG_FILE):
                STREAM.warning(" -> The configuration file seems to have changed since the last session!")
                STREAM.warning(" -> Saved session is no longer valid.")
                STREAM.warning(" -> Start over.")
                self.destroy_session()
                return None, None
            STREAM.debug("vms: %s" % vms)
            last_vm, last_modified_vm_snapshot = vms.pop(-1).split("<--->")
            STREAM.debug("Taken snapshot: %s" % last_modified_vm_snapshot.strip())
            if last_modified_vm_snapshot.strip() == "None":
                last_modified_vm_snapshot = None
            else:
                last_modified_vm_snapshot = last_modified_vm_snapshot.strip()
            ready_vms = [vm.split("<--->")[0].strip() for vm in vms]
            STREAM.debug("Ready vms: %s" % ready_vms)
            # remove already worked vms from working queue
            map(lambda x: self.config_sequence.remove(x), ready_vms)
            # Recreating session file without last got vm to prevent duplication
            with open(self._SESSION_FILE, "w") as sf:
                sf.write("%s\n" % checksum)
                for vm in vms:
                    sf.write(vm)
            return last_vm.strip(), last_modified_vm_snapshot
        return None, None

    def create_session(self):
        config_hash = self.get_hash(self._CONFIG_FILE)
        with open(self._SESSION_FILE, "a") as sf:
            sf.write("%s\n" % config_hash)

    def update_session(self, vm, snapshot="None"):
        with open(self._SESSION_FILE, "a") as sf:
            sf.write("%s <---> %s\n" % (vm, snapshot))

    def destroy_session(self):
        os.remove(self._SESSION_FILE)

    def get_hash(self, filepath):
        with open(filepath, "r") as cf:
            data = cf.read()
        config_hash = hashlib.md5()
        config_hash.update(data)
        return config_hash.hexdigest()

    def args(self):
        parser = optparse.OptionParser('vmaker [options]\n\nOptions:\n  -c <path>  - Specify configuration file.\n'
                                       '  -g         - Generate default configuration file.\n\n'
                                       '  --gfp <path>                  - Generate configuration file, based on specified path.\n'
                                       '  --check-plugin <plugin name>  - Check target plugin.')
        parser.add_option("-c", dest="config_path", type="string", help="Specify config file location")
        parser.add_option("-g", dest="generate_default", action="store_true", help="Generate default config")
        parser.add_option("--gfp", dest="generate_from_path", type="string", help="Generate config from path")
        parser.add_option("--check-plugin", dest="check_plugin", type="string", help="Check target plugin")
        options, args = parser.parse_args()
        if options.config_path:
            self._CONFIG_FILE = options.config_path
        if options.generate_default:
            ConfigController.generate_default_config(self._CONFIG_FILE)
            exit(0)
        if options.generate_from_path:
            ConfigController.generate_from_path(options.generate_from_path)
            exit(0)
        if options.check_plugin:
            PluginController.check_plugin(options.check_plugin)
            exit(0)


if __name__ == "__main__":
    pass
