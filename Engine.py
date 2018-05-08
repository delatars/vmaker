# -*- coding: utf-8 -*-

import sys
import importlib
from subprocess import Popen, PIPE
from datetime import datetime
from auxilary import Fabric
from Managers.RunManager import RunManager
from Logger import STREAM


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
            STREAM.info(">>>>> Initialize %s <<<<<" % self.current_vm.__name__)
            # self.take_snapshot(self.current_vm.name)
            # Fabric.obj = self.current_vm
            # self.plugins_module = importlib.import_module("Plugins")
            # self.do_actions(self.current_vm.actions)
            # self.plugins_module = importlib.import_module("Plugins")

    # recursion function
    def do_actions(self, actions_list):
        def _restore(exception):
            STREAM.warning("==> Exception in vm <%s>:" % self.current_vm.__name__)
            STREAM.error(" -> %s" % exception)
            STREAM.error(" -> Can't proceed with this vm")
            # self.restore_from_snapshot(self.current_vm.name)
            STREAM.info("! - Restore complete, going next...")

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
        STREAM.info("==> Taking a snapshot")
        self.current_vm_snapshot = vm_name+"__"+str(datetime.now())[:-7].replace(" ", "_")
        Popen('VBoxManage snapshot %s take %s' % (vm_name, self.current_vm_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        self.update_session(self.current_vm.__name__, self.current_vm_snapshot)

    def restore_from_snapshot(self):
        STREAM.info("==> Restoring to previous state...")
        Popen('VBoxManage snapshot restore %s' % (self.current_vm_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()


# if __name__ == "__name__":    
upd = Core()
