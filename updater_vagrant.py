# -*- coding: utf-8 -*-
import paramiko
import sys
import os
from subprocess import Popen, PIPE
from time import sleep
from configparser import ConfigParser

class update_vms:
    def vm_start(self, vm_name):
        Popen("vboxmanage startvm %s --type headless" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout)
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                break
            sleep(3)

    def vm_stop(self, vm_name):    
        Popen("VBoxManage controlvm %s acpipowerbutton" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout)
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name not in data:
                break
            sleep(3)

    def connect_to_vm(self):
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("92.53.66.51", username="root", password="siudfy3748asd")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("uname -a")
        print ssh_stdout.read()
        return ssh

    def generate_default_config(self):
        config = ConfigParser()
        cmd = Popen("vboxmanage list vms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        vms = cmd.stdout.read()
        vms = vms.strip().replace('"',"").split("\n")
        for vm in vms:
            config[vm] = {"commands": "cmd1, cmd2, cmd3..."}
        cfg = open("actions.ini", "w")
        config.write(cfg)
        cfg.close()

    def parse_config(self):
        if not os.path.exists('actions.ini'):
            pass
        config = ConfigParser()
        config.read("actions.ini")