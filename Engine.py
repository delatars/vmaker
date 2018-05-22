# -*- coding: utf-8 -*-

import sys
from subprocess import Popen
from datetime import datetime
from time import sleep
from multiprocessing import Process
from traceback import format_exc
from init.args import ConsoleManager
from init.start import RunManager
from utils.Logger import STREAM


class Core(RunManager):

    # self.general_config - dict with general config section items {key: value}
    # self.config - dict with vm objects {vm_name: object(vm)}
    # self.config_sequence - sequence to work with vms list[vm_name, ...]
    # self.loaded_plugins - dict with loaded plugins {plugin_name: object(plugin)}

    def __init__(self):
        ConsoleManager()
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
        def _restore(exception, action, debug=None):
            # This function restore vm to previous state
            STREAM.error(" -> Exception in vm <%s> and action <%s>:" % (self.current_vm.__name__, action))
            STREAM.error(" -> %s" % exception)
            STREAM.debug(debug)
            STREAM.error(" -> Can't proceed with this vm")
            # self.restore_from_snapshot(self.current_vm.name)

        def _get_timeout(keyword):
            try:
                ttk = keyword.time_to_kill
                STREAM.debug("Keyword attribute 'time_to_kill' detected, using it:"
                             " time_to_kill = %s min" % keyword.time_to_kill)
            except AttributeError:
                STREAM.debug("Keyword attribute 'time_to_kill' not detected, using genereal config:"
                             " time_to_kill = %s min" % self.general_config["time_to_kill"])
                ttk = self.general_config["time_to_kill"]
            ttk = int(ttk)*60
            return ttk

        def _process_guard(timeout, process):
            # This function kill proccess if it hung up
            timer = 0
            while 1:
                if process.is_alive():
                    if timer > timeout:
                        process.terminate()
                        STREAM.notice("# # # # # # # # # # # # # END OF %s OUTPUT STREAM # # # # # # # # # # # # #" % action)
                        STREAM.debug("Keyword timeout exceed, Terminated!")
                        raise Exception("Keyword timeout exceed, Terminated!")
                else:
                    if process.exitcode == 0:
                        STREAM.notice("# # # # # # # # # # # # # END OF %s OUTPUT STREAM # # # # # # # # # # # # #" % action)
                        STREAM.info("Keyword successfully exited, going next keyword...")
                        break
                    else:
                        STREAM.notice("# # # # # # # # # # # # # END OF %s OUTPUT STREAM # # # # # # # # # # # # #" % action)
                        raise Exception("Error in keyword!")
                sleep(1)
                if timer % 60 == 0:
                    STREAM.debug("%s min remaining to terminate Keyword!" % str((timeout-timer)/60))
                timer += 1

        for action in actions_list:
            try:
                keyword = self.loaded_plugins[action]
                # Injecting config attributes to plugin
                mutual_keyword = type("mutual_keyword", (keyword, self.current_vm), {})
                ttk = _get_timeout(mutual_keyword)
                try:
                    # Execute plugin in child process
                    STREAM.notice("######################## START OF %s OUTPUT STREAM ########################" % action)
                    keyword_process = Process(target=mutual_keyword().main)
                    keyword_process.start()
                    _process_guard(ttk, keyword_process)
                except Exception as exc:
                    _restore(exc, action, format_exc())
                    return
            except KeyError:
                # Going to alias actions list
                try:
                    self.do_actions(self.current_vm.aliases[action])
                except KeyError as exc:
                    STREAM.error(" -> Unknown action! (%s)" % str(exc))
                    _restore(exc, action, format_exc())
                    return

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
        STREAM.info("==> Restore complete, going next vm...")


# if __name__ == "__name__":
# try:
upd = Core()
# except IOError:
#     print "==> Escalating privilegies"
#     Popen('sudo python %s' % (sys.argv[0]), shell=True, stdout=sys.stdout, stderr=sys.stdout)
#     sys.exit()


