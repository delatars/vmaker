# -*- coding: utf-8 -*-

import sys
from time import sleep
from subprocess import PIPE, Popen
from  Logger import STREAM

class Keyword:
    
    def main(self):
        # - Config attributes
        vm_name = Keyword.vm_name
        #----------------------------------

        def check_vm_status():
            STREAM.info("==> Check Vm status...")
            rvms = Popen(" -> VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                STREAM.info("VM is ON")
                return True
            STREAM.info(" -> VM is turned off")
            return False

        if not check_vm_status():
            STREAM.info(" -> VM already stoped!")
            return
        STREAM.info("==> Attempting to gracefull shutdown VM")
        Popen("VBoxManage controlvm %s acpipowerbutton" % vm_name, shell=True,
                stdout=sys.stdout, stderr=sys.stdout)
        tries = 0
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name not in data:
                break            
            if tries==4:
                STREAM.info(" -> Forcing shutdown VM")
                Popen("VBoxManage controlvm %s poweroff soft" % vm_name, shell=True,stdout=sys.stdout, stderr=sys.stdout).communicate()
                break
            tries += 1
            sleep(5)

if __name__ == "__main__":
    pass
