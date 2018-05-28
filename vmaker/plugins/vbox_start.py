# -*- coding: utf-8 -*-
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM

class Keyword:
    """
    This plugin allows to start your virtual machine.
    Arguments of actions.ini:
    vm_name = name of the virtual machine in VboxManage (example: vm_name = ubuntu1610-amd64_1523264320143_80330)
    """

    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        #----------------------------------
        self.start()

    def check_vm_status(self):
        STREAM.info("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.info(" -> VM is ON")
            return True
        STREAM.info(" -> VM is turned off")
        return False

    def start(self):
        if self.check_vm_status():
            STREAM.info(" -> VM already booted!")
            return
        STREAM.info("==> Starting VM...")
        Popen("VBoxManage startvm %s --type headless" % self.vm_name, shell=True, stdout=PIPE, stderr=PIPE)
        while 1:
            sleep(10)
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if self.vm_name in data:
                break
        STREAM.info(" -> VM successfully booted.")
    

if __name__ == "__main__":
    pass
