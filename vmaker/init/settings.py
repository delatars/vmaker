# -*- coding: utf-8 -*-
import os


class vars:
    WORK_DIR = os.path.join(os.path.expanduser("~"), ".vmaker")
    SESSION_FILE = os.path.join(WORK_DIR, 'vms.session')
    PID_FILE = os.path.join(WORK_DIR, 'vms.pid')
    GENERAL_CONFIG = os.path.join(WORK_DIR, '.vmaker.ini')
    CONFIG_FILE = os.path.join(WORK_DIR, 'default.ini')

    def __init__(self):
        if not os.path.exists(self.WORK_DIR):
            os.mkdir(self.WORK_DIR)
            self.generate_general_config()

    def generate_general_config(self):
        template = """;Mandatory section.      
[General]
; List of enabled plugins, you can create your plugin, put it to the plugins dir and enabling it here.
enabled_plugins = vbox_start, unix_update, vbox_stop, port_forwarding, test, vagrant_export
; Global parameter (in minutes) to the end of which plugin process will be terminated.
;   You can specify your own "kill_timeout" parameter for each action in vm, like <action>_kill_timeout = 10
;   Example: vbox_start_kill_timeout = 5
kill_timeout = 20
; Specify path to output log
log = %s
; Enable/Disable debug prints
debug = false

        """ % os.path.join(os.path.dirname(self.GENERAL_CONFIG), "stdout.log")
        with open(self.GENERAL_CONFIG, "w") as config:
            config.write(template)