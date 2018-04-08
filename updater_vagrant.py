# -*- coding: utf-8 -*-
import paramiko
import sys
import os
from subprocess import Popen, PIPE
from time import sleep
from configparser import ConfigParser


class RunManager(object):
    _SESSION_FILE = '/run/session.vms'
    _PID_FILE = '/run/vms.pid'

    def __init__(self):
        pass

    def create_pid(self):        
        with open(RunManager._PID_FILE, "w") as pf:
            pf.write(str(os.getpid()))

    def check_session(self):
        if os.path.exists(RunManager._PID_FILE):
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

    def update_session(self, vm):
        with open(RunManager._SESSION_FILE, "a") as sf:
            sf.write(vm+"\n")

    def create_session(self):
        with open(RunManager._SESSION_FILE, "w"):
            pass
    
    def destroy_session(self):
        os.remove(RunManager._SESSION_FILE)


class UpdateVms(RunManager):
    _VIRTUALBOXDIR = "~/VirtualBox VMs"

    def __init__(self):
        if os.path.exists(RunManager._PID_FILE):
            with open(RunManager._PID_FILE, "w") as pf:
                pid = pf.readline().strip()
            proc = Popen("ps -aux|awk '{print $2}'", shell=True, stdout=PIPE, stderr=PIPE)
            pids = proc.stdout.read()
            if pid in pids:
                print "Already running! PID: %s" % pid
                sys.exit()
        else:
            self.create_pid()
        self.config = self.load_config()
        super(UpdateVms, self).__init__()

    def main(self):
        for vm, commands in self.config.items():
            self.vm_start(vm)
            connection = self.connect_to_vm("192.168.0.2", "root", "toor")
            for cmd in commands:
                self.command_exec(connection, cmd)
            self.close_ssh_connection(connection)
            self.vm_stop(vm)
            self.export_vm(vm)
            self.update_session(vm)

    def vm_start(self, vm_name):
        Popen("vboxmanage startvm %s --type headless" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout)
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                break
            sleep(3)

    def vm_stop(self, vm_name):    
        Popen("VBoxManage controlvm %s acpipowerbutton" % vm_name, shell=True,
              stdout=sys.stdout, stderr=sys.stdout)
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name not in data:
                break
            sleep(3)

    def connect_to_vm(self, server, user, password):
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=user, password=password)
        return ssh

    def close_ssh_connection(self, connection):
        connection.close()

    def command_exec(self, ssh, command):
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write("y")
        print ssh_stderr.read()

    def export_vm(self, vm):
        exp = Popen("vagrant package --base %s" % os.path.join(UpdateVms._VIRTUALBOXDIR, vm),
                    shell=True, stdout=PIPE, stderr=PIPE)
        print exp.stdout.read()


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

    def load_config(self):
        if not os.path.exists('actions.ini'):
            print "Actions.ini not found! You may generate it by add -g key."
            sys.exit()
        config = ConfigParser()
        config.read("actions.ini")        
        config_cache = {sec:{"commands": [cmd.strip() for cmd in config[sec]["commands"].split(",")]}
                        for sec in config.sections()}
        return config_cache

UpdateVms().generate_default_config()