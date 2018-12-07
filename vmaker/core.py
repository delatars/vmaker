# -*- coding: utf-8 -*-
from time import sleep
from multiprocessing import Process
from vmaker.init.settings import LoadSettings
from vmaker.init.engine import Engine
from vmaker.utils.logger import LoggerOptions, STREAM
from vmaker.utils.reporter import Reporter


class Core(Engine):
    """ Main Class
        - union keywords with objects
        - execute keywords in child processes
        - control child processes execution

        Inheritence:
        config   ->
                   --> engine -> core
        keywords ->
        """

    def __init__(self):
        # Invoke Engine
        try:
            super(Core, self).__init__()
        except KeyboardInterrupt:
            print "\n[!] Job was interrupted by user."
            exit(1)
        # inherited attributes:
        #   self.executions - dict with executions that could be executed like keywords by invoking plugin 'execute_command'
        #                    {action_name: command}
        #   self.config - dict with vm objects {vm_name: object(vm)}
        #   self.config_sequence - sequence to work with virtual machines list[vm_name, ...]
        #   self.loaded_keywords - dict with loaded keywords {keyword_name: object(keyword)}
        STREAM.notice("==> BEGIN.")
        # Connect notification module
        self.reports = Reporter(self.config)
        # Current working vm object
        self.current_vm_obj = None
        # Contains list of already done actions for current working vm object
        self.actions_progress = []
        try:
            self.main()
        except KeyboardInterrupt:
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
            STREAM.error("[!] Job was interrupted by user.")
            STREAM.notice("==> Clearing ourselves")
            self.clearing()

    def main(self):
        for vm in self.config_sequence:
            self.current_vm_obj = self.config[vm]
            self.actions_progress = []
            # Set logger filter
            LoggerOptions.set_component(self.current_vm_obj.__name__)
            result = self.do_actions(self.current_vm_obj.actions)
            if result:
                STREAM.notice("==> There are no more Keywords, going next vm.")
                self.reports.add_report(self.current_vm_obj.__name__, "Success")
            else:
                pass
        self.reports.send_reports()
        STREAM.notice("==> There are no more virtual machines, exiting")
        STREAM.notice("==> END.")

    # recursion function which unpack aliases
    def do_actions(self, actions_list):
        def _restore(exception, action):
            """ The function reverse actions and add ERROR report to reporter """
            LoggerOptions.set_component("Core")
            LoggerOptions.set_action(None)
            self.reports.add_report(self.current_vm_obj.__name__, "ERROR", action)
            STREAM.error(" -> %s" % exception)
            STREAM.error(" -> Can't proceed with this vm")
            STREAM.notice("==> Clearing ourselves")
            self.clearing()

        def _get_timeout():
            """ The function searches for a timeout for the keyword termination """
            try:
                ttk = getattr(self.current_vm_obj, "%s_timeout" % action)
                LoggerOptions.set_component("Core")
                LoggerOptions.set_action(None)
                STREAM.debug(" Assigned 'timeout' for action: %s = %s min" % (action, ttk))
                LoggerOptions.set_component(self.current_vm_obj.__name__)
                LoggerOptions.set_action(action)
            except AttributeError:
                ttk = LoadSettings.TIMEOUT
                LoggerOptions.set_component("Core")
                LoggerOptions.set_action(None)
                STREAM.debug(" Parameter 'timeout' not assigned, for action (%s), using global: %s min" % (action, ttk))
                LoggerOptions.set_component(self.current_vm_obj.__name__)
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
                    LoggerOptions.set_component(self.current_vm_obj.__name__)
                    LoggerOptions.set_action(action)
                timer += 1

        for action in actions_list:
            if action in self.executions.keys():
                keyword = self.execution_get_keyword(self.executions[action])
                setattr(self.current_vm_obj, keyword, self.executions[action])
                action = keyword
            try:
                invoked_keyword = self.invoke_keyword(action)
                self.actions_progress.append(action)
                timeout = _get_timeout()
                try:
                    LoggerOptions.set_component(self.current_vm_obj.__name__)
                    LoggerOptions.set_action(action)
                    # Execute keyword in child process
                    keyword_process = Process(target=invoked_keyword().main)
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

    def execution_get_keyword(self, execution_line):
        """ Method to parse command and make dicision which keyword to use for it """
        if execution_line.strip().startswith("exec:"):
            return "execute_command"
        elif execution_line.strip().startswith("script:"):
            return "execute_script"
        else:
            return "execute_command"

    def invoke_keyword(self, keyword_name):
        """ Method allows to invoke any existed keyword """
        keyword = self.loaded_keywords[keyword_name]
        # Injecting config attributes to keyword obj
        mutual_keyword = type("Keyword", (keyword, self.current_vm_obj), {})
        return mutual_keyword

    def clearing(self):
        """ Clearing method, invoked if job is interrupted or complete unsuccessfully.
            Reverse already done actions by invoking 'clearing' method in each keyword.
            If 'clearing' method not implemented in keyword, doing nothing. """
        LoggerOptions.set_action("clearing")
        for action in reversed(self.actions_progress):
            try:
                invoke = self.invoke_keyword(action)
                getattr(invoke, "clearing")
            except AttributeError:
                STREAM.debug("==> Reverse action '%s':" % action)
                STREAM.debug(" -> Method 'clearing' not implemented in keyword, nothing to do.")
            else:
                STREAM.info("==> Reverse action '%s':" % action)
                invoke().clearing()
        LoggerOptions.set_action(None)


if __name__ == "__main__":
    pass
