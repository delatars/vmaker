# -*- coding: utf-8 -*-
import os
import sys
import re
from subprocess import PIPE, Popen
# Check requirements
try:
    import coloredlogs
    import verboselogs
    import requests
    import bs4
    import glanceclient
    import novaclient
    import paramiko
    from configparser import ConfigParser, NoSectionError
except ImportError as err:
    sys.stderr.write("Can't start vmaker! %s\nYou can install it by using 'pip install'.\n" % err)
    sys.exit(1)


class LoadSettings:
    """Class loads and stores base settings of vmaker
        - Load settings
        - Store settings
        - Generate base configuration file"""
    WORK_DIR = os.path.join(os.path.expanduser("~"), ".vmaker")
    SESSION_FILE = os.path.join(WORK_DIR, '.vms.session')
    PID_FILE = os.path.join(WORK_DIR, '.vms.pid')
    GENERAL_CONFIG_FILENAME = 'vmaker.ini'
    GENERAL_CONFIG = os.path.join(WORK_DIR, GENERAL_CONFIG_FILENAME)
    CONFIG_FILE_PATH = os.path.join(WORK_DIR, 'default.ini')

    ENABLED_PLUGINS = []
    TIMEOUT = 20
    LOG = os.path.join(WORK_DIR, "stdout.log")
    DEBUG = False

    VAGRANT_SERVER_URL = ""
    SMTP_SERVER = ""
    SMTP_PORT = 25
    SMTP_USER = ""
    SMTP_PASS = ""
    SMTP_MAIL_FROM = ""

    def __init__(self):
        self.log = verboselogs.VerboseLogger(__name__)
        coloredlogs.install(fmt='%(asctime)s [Core] [%(levelname)s] %(message)s', logger=self.log)
        process = Popen("VBoxManage -h", shell=True, stdout=PIPE, stderr=PIPE).communicate()
        if len(process[1]) > 0:
            self.log.critical("VboxManage not found!\nvmaker uses VBoxManage to control virtual machines.\n"
                              "Make sure, that you have installed VirtualBox or "
                              "VBoxManage binary in $PATH environment.")
            sys.exit(1)
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
; Examles:
;   enabled_plugins = plugin1, plugin2 - enable only 'plugin1' and 'plugin2'
;   enabled_plugins = all - enable all plugins in plugins dir
;   enabled_plugins = all!(plugin1, plugin2) - enable all plugins in plugins dir except 'plugin1' and 'plugin2'
enabled_plugins = all!(test)
; Global parameter (in minutes) to the end of which plugin process will be terminated.
;   You can specify your own "timeout" parameter for each action in vm, like <action>_timeout = 10
;   Example: vbox_start_timeout = 5
timeout = 20
; Specify path to output log
log = %s
; Enable/Disable debug prints
debug = false
; Url to your vagrant server
;vagrant_server_url = "http:\\localhost"

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

    def enabled_plugins_parser(self, values):
        if values.lower().strip() == "all":
            import vmaker.plugins
            plugins = [plugin[:-3] for plugin in os.listdir(os.path.dirname(vmaker.plugins.__file__))
                       if not plugin.startswith("_") and plugin.endswith("py")]
        elif re.match(r"all!\(.*\)$", values.strip()):
            except_plugins = [plugin.strip() for plugin in
                              values.replace("(", "").replace(")", "").split("!")[1].split(",")]
            import vmaker.plugins
            plugins = [plugin[:-3] for plugin in os.listdir(os.path.dirname(vmaker.plugins.__file__))
                       if not plugin.startswith("_") and plugin.endswith("py")]
            plugins = set(plugins) - set(except_plugins)
        else:
            plugins = [val.strip() for val in values.split(",")]
        return list(plugins)

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
                        if key == "enabled_plugins":
                            values = self.enabled_plugins_parser(value)
                        else:
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
