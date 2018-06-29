# -*- coding: utf-8 -*-
import sys
import re
from subprocess import Popen
from datetime import datetime
from time import sleep
from multiprocessing import Process
from vmaker.init.settings import LoadSettings
from vmaker.init.engine import Engine
from vmaker.utils.logger import LoggerOptions, STREAM
from vmaker.utils.reporter import Reporter


class Core(Engine):
    """Main Class
        - union plugins with objects
        - execute plugins in child processes
        - control child processes execution
        - taking/restoring/deleting snapshots

        Inheritence:
        config  ->
                   --> engine -> Core
        plugins ->
        """

    def __init__(self):
        # Invoke Engine
        super(Core, self).__init__()
        # self.config - dict with vm objects {vm_name: object(vm)}
        # self.config_sequence - sequence to work with vms list[vm_name, ...]
        # self.loaded_plugins - dict with loaded plugins {plugin_name: object(plugin)}
        STREAM.notice("==> BEGIN.")
        # Connect notification module
        self.reports = Reporter(self.config)
        # Current working vm object
        self.current_vm_obj = None
        # Current working config section name
        self.current_vm = None
        # Flag if snapshot needed for vm
        self.exists_snapshot = False
        # Flag if start from restored session
        self.is_session = False
        vm, self.current_vm_obj_snapshot = self.check_session()
        if vm is None:
            self.create_session()
        else:
            # If job is interrupted, restore to previous state and restore from snapshot if needed
            self.is_session = True
            if self.current_vm_obj_snapshot is not None:
                vm_name = self.current_vm_obj_snapshot.split("__")[0]
                self.current_vm_obj = self.config[vm]
                self.restore_from_snapshot(vm_name)
        self.main()
    
    def main(self):
        for vm in self.config_sequence:
            self.current_vm = vm
            self.current_vm_obj = self.config[vm]
            # if vm exists "snapshot" attribute, creating snapshot
            try:
                if self.current_vm_obj.snapshot.lower() == "true" and self.is_session is False:
                    self.exists_snapshot = True
                    self.take_snapshot(self.current_vm_obj.vm_name)
                    self.update_session(vm, self.current_vm_obj_snapshot)
                elif self.current_vm_obj.snapshot.lower() == "true" and self.is_session is True:
                    self.exists_snapshot = True
                    self.update_session(vm, self.current_vm_obj_snapshot)
                else:
                    self.update_session(vm)
            except AttributeError:
                self.update_session(vm)
            # Set logger filter
            LoggerOptions.set_component(self.current_vm)
            result = self.do_actions(self.current_vm_obj.actions)
            if result:
                STREAM.notice("==> There are no more Keywords, going next vm.")
            else:
                pass
            # If all actions are ok, delete a snapshot.
            if self.exists_snapshot:
                self.delete_snapshot(self.current_vm_obj.vm_name)
        self.reports.send_reports()
        STREAM.notice("==> There are no more virtual machines, exiting")
        STREAM.notice("==> END.")
        self.destroy_session()

    # recursion function which unpack aliases
    def do_actions(self, actions_list):
        def _restore(exception, action):
            # This function restore vm to previous state
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
            with open(LoadSettings.LOG, "r") as log:
                log.seek(-3000, 2)
                data = log.read()
                index = data.rfind("Traceback")
                report_exc = data[index:]
                report_exc = re.sub(r"\d\d\d\d-\d\d-\d\d.*", r"", report_exc).strip()
                self.reports.add_report(self.current_vm_obj.__name__, action, report_exc)
            STREAM.error(" -> Exception in vm <%s> and action <%s>:" % (self.current_vm_obj.__name__, action))
            STREAM.error(" -> %s" % exception)
            STREAM.error(" -> Can't proceed with this vm")
            STREAM.notice("==> Clearing ourselves")
            if self.exists_snapshot:
                self.restore_from_snapshot(self.current_vm_obj.vm_name)
            else:
                invoked = self.invoke_plugin("vbox_stop")
                try:
                    getattr(invoked, "vm_name")
                    invoked().main()
                except AttributeError:
                    pass

        def _get_timeout():
            try:
                ttk = getattr(self.current_vm_obj, "%s_kill_timeout" % action)
                LoggerOptions.set_component("Core")
                LoggerOptions.set_action(None)
                STREAM.debug(" Assigned 'kill_timeout' for action: %s = %s min" % (action, ttk))
                LoggerOptions.set_component(self.current_vm)
                LoggerOptions.set_action(action)
            except AttributeError:
                ttk = LoadSettings.KILL_TIMEOUT
                LoggerOptions.set_component("Core")
                LoggerOptions.set_action(None)
                STREAM.debug(" Parameter 'kill_timeout' not assigned, for action, using global: %s = %s min" % (action, ttk))
                LoggerOptions.set_component(self.current_vm)
                LoggerOptions.set_action(action)
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
                        raise Exception("Keyword timeout exceed, Terminated!")
                else:
                    if process.exitcode == 0:
                        break
                    else:
                        raise Exception("Exception in keyword!")
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
                invoked_plugin = self.invoke_plugin(action)
                ttk = _get_timeout()
                try:
                    LoggerOptions.set_component(self.current_vm)
                    LoggerOptions.set_action(action)
                    # Execute plugin in child process
                    keyword_process = Process(target=invoked_plugin().main)
                    keyword_process.start()
                    # Monitoring running proccess
                    _process_guard(ttk, keyword_process)
                except Exception as exc:
                    _restore(exc, action)
                    return False
            except KeyError:
                # Going to alias actions list
                try:
                    self.do_actions(self.current_vm_obj.aliases[action])
                except KeyError as exc:
                    STREAM.error(" -> Unknown action! (%s)" % str(exc))
                    _restore(exc, action)
                    return False
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
        return True

    def invoke_plugin(self, plugin_name):
        keyword = self.loaded_plugins[plugin_name]
        # Injecting config attributes to plugin
        mutual_keyword = type("Keyword", (keyword, self.current_vm_obj), {})
        return mutual_keyword

    def take_snapshot(self, vm_name):
        invoked_plugin = self.invoke_plugin("vbox_stop")
        invoked_plugin().main()
        STREAM.info("==> Taking a snapshot")
        self.current_vm_obj_snapshot = vm_name+"__"+str(datetime.now())[:-7].replace(" ", "_")
        Popen('VBoxManage snapshot %s take %s' % (vm_name, self.current_vm_obj_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()

    def restore_from_snapshot(self, vm_name):
        invoked_plugin = self.invoke_plugin("vbox_stop")
        invoked_plugin().main()
        STREAM.info("==> Restoring to previous state...")
        Popen('VBoxManage snapshot %s restore %s' % (vm_name, self.current_vm_obj_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        STREAM.info("==> Restore complete.")

    def delete_snapshot(self, vm_name):
        STREAM.info("==> Deleting snapshot.")
        Popen('VBoxManage snapshot %s delete %s' % (vm_name, self.current_vm_obj_snapshot),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()


if __name__ == "__main__":
    pass
