# -*- coding: utf-8 -*-
import os
import sys
import re
from subprocess import PIPE, Popen
# Check requirements
try:
    import ansible
    import coloredlogs
    import verboselogs
    import requests
    import bs4
    import glanceclient
    import novaclient
    import paramiko
    import pathos
    import scp
    from configparser import ConfigParser, NoSectionError
except ImportError as err:
    sys.stderr.write("Can't start vmaker! %s\nYou can install it by using 'pip install'.\n" % err)
    sys.exit(1)


class LoadSettings:
    """ Class loads and stores base settings of vmaker
        - Load settings
        - Store settings
        - Generate base configuration file"""
    WORK_DIR = os.path.join(os.path.expanduser("~"), ".vmaker")
    SESSION_FILE = os.path.join(WORK_DIR, '.vms.session')
    GENERAL_CONFIG_FILENAME = 'vmaker.ini'
    GENERAL_CONFIG = os.path.join(WORK_DIR, GENERAL_CONFIG_FILENAME)
    CONFIG_FILE_PATH = os.path.join(WORK_DIR, 'default.ini')

    ENABLED_KEYWORDS = []
    TIMEOUT = 20
    LOG = os.path.join(WORK_DIR, "stdout.log")
    DEBUG = False

    VAGRANT_SERVER_URL = ""
    SMTP_SERVER = ""
    SMTP_PORT = 25
    SMTP_USER = ""
    SMTP_PASS = ""
    SMTP_MAIL_FROM = "reports@vmaker.com"

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
        template = """[General]
; The list of Keywords with which will work "vmaker" (directory: vmaker/keywords).
; Examples:
;   enabled_keywords = vbox_start, vbox_stop - enable only 'vbox_start' and 'vbox_stop'
;   enabled_keywords = all - enable all keywords
;   enabled_keywords = all!(vbox_start, vbox_stop) - enable all keywords, excepts 'vbox_start' and 'vbox_stop'
enabled_keywords = all
; Global parameter that sets a time limit for keyword execution, after which the keyword will be terminated. (time sets in minutes)
timeout = 20
; Log file location
log = %s
; Enable/Disable debug messages
debug = false
; Url of the Vagrant server
;vagrant_server_url = "http:\\localhost"

; The following Settings used for connecting to the smtp server to send email notifications
;smtp_server = 
;smtp_port = 25
;smtp_mail_from = reports@vmaker.com
; Authentication
;smtp_user = 
;smtp_pass = 

; Also you can specify cluster connection settings here (used for keywords that work with openstack)
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

    def enabled_keywords_parser(self, values):
        if values.lower().strip() == "all":
            import vmaker.keywords
            keywords = [keyword[:-3] for keyword in os.listdir(os.path.dirname(vmaker.keywords.__file__))
                       if not keyword.startswith("_") and keyword.endswith("py")]
        elif re.match(r"all!\(.*\)$", values.strip()):
            except_keywords = [keyword.strip() for keyword in
                              values.replace("(", "").replace(")", "").split("!")[1].split(",")]
            import vmaker.keywords
            keywords = [keyword[:-3] for keyword in os.listdir(os.path.dirname(vmaker.keywords.__file__))
                       if not keyword.startswith("_") and keyword.endswith("py")]
            keywords = set(keywords) - set(except_keywords)
        else:
            keywords = [val.strip() for val in values.split(",")]
        return list(keywords)

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
                        if key == "enabled_keywords":
                            values = self.enabled_keywords_parser(value)
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
