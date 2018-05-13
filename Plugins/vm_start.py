# -*- coding: utf-8 -*-
import sys
from time import sleep
from subprocess import PIPE, Popen
from Logger import STREAM

class Keyword:

    def main(self):
        # - Config attributes
        vm_name = Keyword.vm_name
        #----------------------------------

        def check_vm_status():
            STREAM.info("==> Check Vm status.")
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                STREAM.info(" -> VM is ON")
                return True
            STREAM.info(" -> VM is turned off")
            return False

        if check_vm_status():
            STREAM.info(" -> VM already booted!")
            return
        STREAM.info("==> Forwarding ssh ports 22(guest) => 2020(host)")
        Popen("vboxmanage modifyvm %s --natpf1 delete vm_ssh" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        Popen("vboxmanage modifyvm %s --natpf1 vm_ssh,tcp,127.0.0.1,2020,,22" % vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        STREAM.info("==> Starting VM...")
        Popen("vboxmanage startvm %s --type headless" % vm_name, shell=True, stdout=PIPE, stderr=PIPE)
        while 1:
            sleep(10)
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if vm_name in data:
                break
        STREAM.info(" -> VM successfully booted.")
    

if __name__ == "__main__":
    pass
