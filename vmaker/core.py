# -*- coding: utf-8 -*-
import sys
from subprocess import Popen
from datetime import datetime
from time import sleep
from multiprocessing import Process
from vmaker.init.engine import Engine
from vmaker.utils.logger import LoggerOptions, STREAM


class Core(Engine):

    # self.general_config - dict with general config section items {key: value}
    # self.config - dict with vm objects {vm_name: object(vm)}
    # self.config_sequence - sequence to work with vms list[vm_name, ...]
    # self.loaded_plugins - dict with loaded plugins {plugin_name: object(plugin)}

    def __init__(self):
        # Invoke Engine
        super(Core, self).__init__()
        # Current working vm object
        self.current_vm_obj = None
        # Current working config section name
        self.current_vm = None
        self.need_snapshot = False
        vm, self.current_vm_obj_snapshot = self.check_session()
        # If job is interrupted, restore to previous state and restore from snapshot if needed
        if self.current_vm_obj_snapshot is not None and self.current_vm_obj_snapshot != "None":
            vm_name = self.current_vm_obj_snapshot.split("__")[0]
            self.restore_from_snapshot(vm_name)
        # Entrypoint
        self.main()
    
    def main(self):
        for vm in self.config_sequence:
            self.current_vm = vm
            self.current_vm_obj = self.config[vm]
            # if vm exists "snapshot" attribute, creating snapshot
            if self.current_vm_obj.snapshot.lower() == "true":
                self.need_snapshot = True
                self.take_snapshot(self.current_vm_obj.vm_name)
                self.update_session(vm, self.current_vm_obj_snapshot)
            else:
                self.update_session(vm)
            # Set logger filter
            LoggerOptions.set_component(self.current_vm)
            self.do_actions(self.current_vm_obj.actions)
            STREAM.notice("==> There are no more Keywords, going next vm.")
            if self.need_snapshot:
                self.delete_snapshot(self.current_vm_obj.vm_name)
        STREAM.notice("==> There are no more virtual machines, exiting")
        self.destroy_session()

    # recursion function which unpack aliases
    def do_actions(self, actions_list):
        def _restore(exception, action):
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
            # This function restore vm to previous state
            STREAM.error(" -> Exception in vm <%s> and action <%s>:" % (self.current_vm_obj.__name__, action))
            STREAM.error(" -> %s" % exception)
            STREAM.error(" -> Can't proceed with this vm")
            if self.need_snapshot:
                self.restore_from_snapshot(self.current_vm_obj.vm_name)

        def _get_timeout():
            try:
                ttk = getattr(self.current_vm_obj, "%s_kill_timeout" % action)
                STREAM.debug(" Assigned 'kill_timeout' for action: %s = %s min" % (action, ttk))
            except AttributeError:
                ttk = self.general_config["kill_timeout"]
                STREAM.debug(" Parameter 'kill_timeout' not assigned, for action, using global: %s = %s min" % (action, ttk))
            ttk = int(ttk)*60
            return ttk

        def _process_guard(timeout, process):
            # This function kill proccess if it hung up
            timer = 0
            while 1:
                if process.is_alive():
                    if timer > timeout:
                        process.terminate()
                        LoggerOptions.set_component("Core")
                        LoggerOptions.set_action(None)
                        STREAM.debug("==> Keyword timeout exceed, Terminated!")
                        raise Exception("==> Keyword timeout exceed, Terminated!")
                else:
                    if process.exitcode == 0:
                        break
                    else:
                        raise Exception("Error in keyword!")
                sleep(1)
                if timer % 60 == 0:
                    LoggerOptions.set_component("Core")
                    LoggerOptions.set_action(None)
                    STREAM.debug("%s min remaining to terminate Keyword!" % str((timeout-timer)/60))
                    LoggerOptions.set_component(self.current_vm)
                    LoggerOptions.set_action(action)
                timer += 1

        for action in actions_list:
            try:
                keyword = self.loaded_plugins[action]
                # Injecting config attributes to plugin
                mutual_keyword = type("Keyword", (keyword, self.current_vm_obj), {})
                ttk = _get_timeout()
                try:
                    LoggerOptions.set_component(self.current_vm)
                    LoggerOptions.set_action(action)
                    # Execute plugin in child process
                    keyword_process = Process(target=mutual_keyword().main)
                    keyword_process.start()
                    # Monitoring running proccess
                    _process_guard(ttk, keyword_process)
                except Exception as exc:
                    _restore(exc, action)
                    return
            except KeyError:
                # Going to alias actions list
                try:
                    self.do_actions(self.current_vm_obj.aliases[action])
                except AttributeError as exc:
                    STREAM.error(" -> Unknown action! (%s)" % str(exc))
                    _restore(exc, action)
                    return
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)

    def take_snapshot(self, vm_name):
        STREAM.info("==> Taking a snapshot")
        self.current_vm_obj_snapshot = vm_name+"__"+str(datetime.now())[:-7].replace(" ", "_")
        Popen('VBoxManage snapshot %s take %s' % (vm_name, self.current_vm_obj_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()

    def restore_from_snapshot(self, vm_name):
        STREAM.info("==> Restoring to previous state...")
        Popen('VBoxManage snapshot %s restore %s' % (vm_name, self.current_vm_obj_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        STREAM.info("==> Restore complete, going next vm...")

    def delete_snapshot(self, vm_name):
        STREAM.info("==> Deleting snapshot.")
        Popen('VBoxManage snapshot %s delete %s' % (vm_name, self.current_vm_obj_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()


def entry():
    upd = Core()


if __name__ == "__main__":
    entry()