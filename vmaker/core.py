# -*- coding: utf-8 -*-
import re
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

        Inheritence:
        config  ->
                   --> engine -> core
        plugins ->
        """

    def __init__(self):
        # Invoke Engine
        try:
            super(Core, self).__init__()
        except KeyboardInterrupt:
            print "\nJob was interrupted by user."
            exit(1)
        # inherited attributes:
        #   self.config - dict with vm objects {vm_name: object(vm)}
        #   self.config_sequence - sequence to work with virtual machines list[vm_name, ...]
        #   self.loaded_plugins - dict with loaded plugins {plugin_name: object(plugin)}
        STREAM.notice("==> BEGIN.")
        # Connect notification module
        self.reports = Reporter(self.config)
        # Current working vm object
        self.current_vm_obj = None
        # Current working config section name
        self.current_vm = None
        try:
            self.main()
        except KeyboardInterrupt:
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
            STREAM.error("==> Job was interrupted by user.")
            STREAM.notice("==> Clearing ourselves")
            self.vbox_stop()

    def main(self):
        for vm in self.config_sequence:
            self.current_vm = vm
            self.current_vm_obj = self.config[vm]
            # Set logger filter
            LoggerOptions.set_component(self.current_vm)
            result = self.do_actions(self.current_vm_obj.actions)
            if result:
                STREAM.notice("==> There are no more Keywords, going next vm.")
            else:
                pass
        self.reports.send_reports()
        STREAM.notice("==> There are no more virtual machines, exiting")
        STREAM.notice("==> END.")

    # recursion function which unpack aliases
    def do_actions(self, actions_list):
        def _restore(exception, action):
            """The function restore vm to previous state"""
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
            if LoadSettings.DEBUG:
                with open(LoadSettings.LOG, "r") as log:
                    log.seek(-3000, 2)
                    data = log.read()
                    index = data.rfind("Traceback")
                    report_exc = data[index:]
                    report_exc = re.sub(r"\d\d\d\d-\d\d-\d\d.*", r"", report_exc).strip()
                self.reports.add_report(self.current_vm_obj.__name__, action, report_exc)
            else:
                with open(LoadSettings.LOG, "r") as log:
                    report_exc = log.readlines()[-1]
                self.reports.add_report(self.current_vm_obj.__name__, action, report_exc)
            STREAM.error(" -> %s" % exception)
            STREAM.error(" -> Can't proceed with this vm")
            STREAM.notice("==> Clearing ourselves")
            self.vbox_stop()

        def _get_timeout():
            """The function searches for a timeout for the keyword termination"""
            try:
                ttk = getattr(self.current_vm_obj, "%s_timeout" % action)
                LoggerOptions.set_component("Core")
                LoggerOptions.set_action(None)
                STREAM.debug(" Assigned 'timeout' for action: %s = %s min" % (action, ttk))
                LoggerOptions.set_component(self.current_vm)
                LoggerOptions.set_action(action)
            except AttributeError:
                ttk = LoadSettings.TIMEOUT
                LoggerOptions.set_component("Core")
                LoggerOptions.set_action(None)
                STREAM.debug(" Parameter 'timeout' not assigned, for action (%s), using global: %s min" % (action, ttk))
                LoggerOptions.set_component(self.current_vm)
                LoggerOptions.set_action(action)
            ttk = int(ttk)*60
            return ttk

        def _process_guard(timeout, process):
            # This function kill child proccess if timeout exceed
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
                timeout = _get_timeout()
                try:
                    LoggerOptions.set_component(self.current_vm)
                    LoggerOptions.set_action(action)
                    # Execute plugin in child process
                    keyword_process = Process(target=invoked_plugin().main)
                    keyword_process.start()
                    # Monitoring running proccess
                    _process_guard(timeout, keyword_process)
                except Exception as exc:
                    _restore(exc, action)
                    return False
            except KeyError:
                # Going to alias actions list
                try:
                    result = self.do_actions(self.current_vm_obj.aliases[action])
                    if result is False:
                        return False
                except KeyError as exc:
                    STREAM.error(" -> Unknown action! (%s)" % str(exc))
                    _restore(exc, action)
                    return False
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
        return True

    def invoke_plugin(self, plugin_name):
        """Method allows to invoke any existed plugin"""
        keyword = self.loaded_plugins[plugin_name]
        # Injecting config attributes to plugin
        mutual_keyword = type("Keyword", (keyword, self.current_vm_obj), {})
        return mutual_keyword

    def vbox_stop(self):
        """Uses plugin vbox_stop"""
        LoggerOptions.set_action("clearing")
        invoked = self.invoke_plugin("vbox_stop")
        try:
            getattr(invoked, "vm_name")
            invoked().main()
        except AttributeError:
            pass
        LoggerOptions.set_action(None)


if __name__ == "__main__":
    pass
