# -*- coding: utf-8 -*-
import sys
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This plugin allows to stop your virtual machine.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in VboxManage (example: vm_name = ubuntu1610-amd64_1523264320143_80330)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name']

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        #----------------------------------
        self.stop()

    def check_vm_status(self):
        STREAM.info("==> Check Vm status...")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.info("VM is ON")
            return True
        STREAM.info(" -> VM is turned off")
        return False

    def stop(self):
        if not self.check_vm_status():
            STREAM.info(" -> VM already stoped!")
            return
        STREAM.info("==> Attempting to gracefull shutdown VM")
        Popen("VBoxManage controlvm %s acpipowerbutton" % self.vm_name, shell=True,
                stdout=sys.stdout, stderr=sys.stdout)
        tries = 0
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if self.vm_name not in data:
                break            
            if tries > 5:
                STREAM.info(" -> Forcing shutdown VM")
                Popen("VBoxManage controlvm %s poweroff soft" % self.vm_name, shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
                break
            tries += 1
            sleep(5)


if __name__ == "__main__":
    pass
