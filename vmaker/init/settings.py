# -*- coding: utf-8 -*-
import os
import sys
from configparser import ConfigParser, NoSectionError
import coloredlogs
import verboselogs


class LoadSettings:
    WORK_DIR = os.path.join(os.path.expanduser("~"), ".vmaker")
    SESSION_FILE = os.path.join(WORK_DIR, '.vms.session')
    PID_FILE = os.path.join(WORK_DIR, '.vms.pid')
    GENERAL_CONFIG_FILENAME = '.vmaker.ini'
    GENERAL_CONFIG = os.path.join(WORK_DIR, GENERAL_CONFIG_FILENAME)
    CONFIG_FILE_PATH = os.path.join(WORK_DIR, 'default.ini')

    ENABLED_PLUGINS = []
    TIMEOUT = 20
    LOG = os.path.join(WORK_DIR, "stdout.log")
    DEBUG = False
    SMTP_SERVER = ""
    SMTP_PORT = 25
    SMTP_USER = ""
    SMTP_PASS = ""

    def __init__(self):
        self.log = verboselogs.VerboseLogger(__name__)
        coloredlogs.install(fmt='%(asctime)s [Core] [%(levelname)s] %(message)s', logger=self.log)
        if not os.path.exists(self.WORK_DIR):
            self.log.warning("%s not found and will be generated!" % self.GENERAL_CONFIG_FILENAME)
            os.mkdir(self.WORK_DIR)
            self.generate_general_config()
            self.log.success("Generated: %s" % self.GENERAL_CONFIG)
        if not os.path.exists(self.GENERAL_CONFIG):
            self.log.warning("%s not found and will be generated!" % self.GENERAL_CONFIG_FILENAME)
            self.generate_general_config()
            self.log.success("Generated: %s" % self.GENERAL_CONFIG)
        self.load_general_config()

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

; Email notifications connection settings
;smtp_server = 
;smtp_port = 
; Authentication
;smtp_user = 
;smtp_pass = 

; You can specify cluster connection settings here to use it in openstack_export plugin
;  Or you may use separate configuration file to keep cluster settings
;[openstack_cluster1]
;auth_url=https://localhost:5000/v3
;username=root
;password=toor
;project_name=project1
;user_domain_id=default
;project_domain_id=default
;ca_cert=/etc/ssl/certs/localhost.pem
        """ % os.path.join(self.WORK_DIR, "stdout.log")
        with open(self.GENERAL_CONFIG, "w") as config:
            config.write(template)

    def load_general_config(self):
        config = ConfigParser()
        config.read(self.GENERAL_CONFIG)
        try:
            general_config = {key.strip(): value.strip() for key, value in config.items("General")}
        except NoSectionError:
            self.log.critical("%s Error: Section <General> does not exist!\nExitting..." % self.GENERAL_CONFIG_FILENAME)
            sys.exit()
        for key, value in general_config.items():
            try:
                attr = getattr(self, key.upper())
            except AttributeError:
                pass
            else:
                if value == "":
                    pass
                else:
                    if isinstance(attr, list):
                        values = [val.strip() for val in value.split(",")]
                        setattr(LoadSettings, key.upper(), values)
                    elif isinstance(attr, str):
                        setattr(LoadSettings, key.upper(), value)
                    elif isinstance(attr, bool):
                        try:
                            int(value)
                        except ValueError:
                            if value.lower() == "true":
                                value = True
                            elif value.lower() == "false":
                                value = False
                            else:
                                value = False
                            setattr(LoadSettings, key.upper(), value)
                        else:
                            setattr(LoadSettings, key.upper(), int(value))
                    elif isinstance(attr, int):
                        setattr(LoadSettings, key.upper(), int(value))
