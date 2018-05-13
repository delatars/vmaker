# -*- coding: utf-8 -*-

import sys
from subprocess import Popen, PIPE
from datetime import datetime
from time import sleep
from multiprocessing import Process
from Managers.RunManager import RunManager
from Logger import STREAM



class Core(RunManager):

    # self.general_config - dict with general config section items {key: value}
    # self.config - dict with vm objects {vm_name: object(vm)}
    # self.config_sequence - sequence to work with vms list[vm_name, ...]
    # self.loaded_plugins - dict with loaded plugins {plugin_name: object(plugin)}

    def __init__(self):
        super(Core, self).__init__()
        # Current working vm
        self.current_vm = None
        self.current_vm_snapshot = self.check_session()
        # If job is interrupted, restore to previous state
        if self.current_vm_snapshot is not None:
            self.restore_from_snapshot()
        # Current working plugin
        self.plugins_module = None
        self.main()
    
    def main(self):
        for vm in self.config_sequence:
            self.current_vm = self.config[vm]
            STREAM.info(">>>>> Initialize %s <<<<<" % self.current_vm.__name__)
            # self.take_snapshot(self.current_vm.name)
            self.do_actions(self.current_vm.actions)

    # recursion function which unpack aliases
    def do_actions(self, actions_list):
        def _restore(exception, action):
            # This function restore vm to previous state
            STREAM.error(" -> Exception in vm <%s> and action <%s>:" % (self.current_vm.__name__, action))
            STREAM.error(" -> %s" % exception)
            STREAM.error(" -> Can't proceed with this vm")
            # self.restore_from_snapshot(self.current_vm.name)
            STREAM.info("==> Restore complete, going next vm...")

        def _get_timeout(keyword):
            try:
                ttk = keyword.time_to_kill
            except AttributeError:
                ttk = self.general_config["time_to_kill"]
            ttk = int(ttk)*60
            return ttk

        def _process_guard(timeout, process, action):
            # This function kill proccess if it hung up
            timer = 0
            while 1:
                if process.is_alive():
                    if timer > timeout:
                        process.terminate()
                        _restore("Keyword timeout exceed, Terminated!", )
                        break
                else:
                    print process.exitcode()
                    STREAM.info("Keyword successfully exited, going next keyword...")
                    break
                sleep(1)
                timer += 1

        for action in actions_list:
            try:
                keyword = self.loaded_plugins[action]
                # Injecting config attributes to plugin
                mutual_keyword = type("new_cls", (keyword, self.current_vm), {})
                try:
                    # Execute plugin in child process
                    ttk = _get_timeout(mutual_keyword)
                    keyword_process = Process(target=mutual_keyword().main)
                    keyword_process.start()
                    _process_guard(ttk, keyword_process, action)
                except Exception as exc:
                    _restore(exc, action)
                    break
            except KeyError:
                # Going to alias actions list
                try:
                    self.do_actions(self.current_vm.aliases[action])
                except KeyError as exc:
                    STREAM.error(" -> Unknown action! (%s)" % str(exc))
                    _restore(exc, action)
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
