# -*- coding: utf-8 -*-

############################################################################################
# This module provide you to write your own action keywords and use it in Actions.ini
# Requirements:
#   - Keywords must be class objects
#   - Keywords names must be started with <Keyword_> prefix example: class Keyword_my:
#   - Each Keywords must contain <main> method, it's an entrypoint of Keyword
#   - You can specify your attributes in Actions.ini and use it in your keywords
############################################################################################

#############################################
# - metaclass to build classes in that module
# - Do not delete it!
from auxilary import VmsMetaclass
__metaclass__ = VmsMetaclass
#############################################

############################################################################################
import paramiko
import sys
from subprocess import Popen, PIPE
from time import sleep


class Keyword_update:

    def main(self):
        pass

    def connect_to_vm(self, server, user, password):
        print "==> Connecting to VM...... ",
        server, port = server.split(":")        
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(server, port=int(port), username=user, password=password)
        except paramiko.ssh_exception.SSHException:
            print("Fail")
            print "==> Retry: Connecting to VM...... ",
            sleep(10)
            ssh.connect(server, port=int(port), username=user, password=password)
        print "OK"
        return ssh

    def close_ssh_connection(self, connection):
        connection.close()

    def command_exec(self, ssh, command):
        print "==> Executing command: %s" % command
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write("y")
        ssh_stdin.write("\n")
        ssh_stdin.flush()
        print ssh_stdout.read()


class Keyword_test:

    def main(self):
        print "Testing"  # Keyword_test.port


class Keyword_vm_start:

    def main(self):
        # - Config attributes
        vm_name = Keyword_vm_start.vm_name
        #----------------------------------

        def check_vm_status():
            print "==> Check Vm status......",
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                print "VM is ON"
                return True
            print "VM is turned off"
            return False

        if check_vm_status():
            print "VM already booted!"
            return
        print "==> Forwarding ssh ports 22(guest) => 2020(host)"
        Popen("vboxmanage modifyvm %s --natpf1 delete vm_ssh" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        Popen("vboxmanage modifyvm %s --natpf1 vm_ssh,tcp,127.0.0.1,2020,,22" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        print "==> Starting VM......",
        Popen("vboxmanage startvm %s --type headless" % vm_name, shell=True, stdout=PIPE, stderr=PIPE)
        while 1:
            sleep(10)
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                break            
        print "OK"    
    

class Keyword_vm_stop:
    
    def main(self):
        # - Config attributes
        vm_name = Keyword_vm_start.vm_name
        #----------------------------------

        def check_vm_status():
            print "==> Check Vm status......",
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                print "VM is ON"
                return True
            print "VM is turned off"
            return False

        if not check_vm_status():
            print "VM already stoped!"
            return
        print "==> Attempting to gracefull shutdown VM"
        Popen("VBoxManage controlvm %s acpipowerbutton" % vm_name, shell=True,
                stdout=sys.stdout, stderr=sys.stdout)
        tries = 0
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name not in data:
                break            
            if tries==4:
                print " |= Forcing shutdown VM"
                Popen("VBoxManage controlvm %s poweroff soft" % vm_name, shell=True,stdout=sys.stdout, stderr=sys.stdout).communicate()
                break
            tries += 1
            sleep(5)

if __name__=="__main__":
    pass
