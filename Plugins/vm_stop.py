# -*- coding: utf-8 -*-

import sys
from time import sleep
from subprocess import PIPE, Popen
    

class Keyword:
    
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
