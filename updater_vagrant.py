# -*- coding: utf-8 -*-
import paramiko
import sys
import os
from subprocess import Popen, PIPE
from time import sleep
from configparser import ConfigParser
from datetime import datetime
import Plugins


class RunManager(object):
    _SESSION_FILE = '/run/vms.session'
    _PID_FILE = '/run/vms.pid'

    def __init__(self):
        self.config = self.load_config()
        self.check_session()

    def create_pid(self):        
        with open(RunManager._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def check_session(self):
        if os.path.exists(RunManager._SESSION_FILE):
            ch = ["y", "Y", "n", "N"]
            while 1:
                choice = raw_input("==> Detect a previous uncomplete session.\n\
 |- Would you like to continue it? (y/n) => ")
                if choice in ch:
                    break
            if choice in ch[:2]:
                with open(RunManager._SESSION_FILE, "r") as sf:
                    vms = sf.readlines()
                for vm in vms:
                    del(self.config[vm.strip()])
            else:
                self.destroy_session()
                self.create_session()
        self.create_session()

    def update_session(self, vm):
        with open(RunManager._SESSION_FILE, "a") as sf:
            sf.write(vm+"\n")

    def create_session(self):
        with open(RunManager._SESSION_FILE, "w"):
            pass
    
    def destroy_session(self):
        os.remove(RunManager._SESSION_FILE)

    @staticmethod
    def generate_default_config():
        config = ConfigParser()
        cmd = Popen("vboxmanage list vms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        vms = cmd.stdout.read()
        vms = vms.strip().replace('"',"").split("\n")
        for vm in vms:
            config[vm] = {"actions": "keyword1, keyword2, keyword3..."}
        cfg = open("actions.ini", "w")
        config.write(cfg)
        cfg.close()

    def load_config(self):
        if not os.path.exists('actions.ini'):
            print "Actions.ini not found! You may generate it by add -g key."
            sys.exit()
        config = ConfigParser()
        config.read("actions.ini")
        config_cache = {sec:{"commands": [cmd.strip() for cmd in config[sec]["commands"].split(",")]}
                        for sec in config.sections()}
        return config_cache


class Core(RunManager):
    _VIRTUALBOXDIR = "~/VirtualBox VMs"

    def __init__(self):
        if os.path.exists(RunManager._PID_FILE):
            with open(RunManager._PID_FILE, "r") as pf:
                pid = pf.readline().strip()
            proc = Popen("ps -aux|awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE)
            pids = proc.stdout.read()
            if pid in pids:
                print "Already running! PID: %s" % pid
                sys.exit()
        else:
            self.create_pid()        
        super(Core, self).__init__()
        self.main()

    def main(self):

        for vm, commands in self.config.items():            
            # connection = self.connect_to_vm("127.0.0.1:2020", "root", "root")
            for cmd in commands["commands"]:
                keyword = getattr(Plugins, "Keyword_"+cmd)
                keyword(vm)
        self.destroy_session()

    def make_snapshot(self, vm_name):
        print("==> Taking a snapshot")
        Popen('VBoxManage snapshot %s take %s' % (vm_name, vm_name+"__"+str(datetime.now())[:-7].replace(" ","_") ),
         shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()        

    def export_vm(self, vm):
        Popen("vagrant package --base %s" % os.path.join(Core._VIRTUALBOXDIR, vm),
                    shell=True, stdout=sys.stdout, stderr=sys.stderr).communicate()

upd = Core()