# -*- coding: utf-8 -*-
import paramiko
import sys
from subprocess import Popen, PIPE
from time import sleep

cmd1 = "vboxmanage list vms | awk '{print $1}'"

def vm_start(vm_name):
    Popen("vboxmanage startvm %s --type headless" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout)
    while 1:
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if vm_name in data:
            break
        sleep(3)

def vm_stop(vm_name):    
    Popen("VBoxManage controlvm %s acpipowerbutton" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout)
    while 1:
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if vm_name not in data:
            break
        sleep(3)

def connect_to_vm(username, password):
    ssh = paramiko.SSHClient()
    ssh.connect("10.10.10.1", username=username, password=password)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)