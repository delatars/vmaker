# -*- coding: utf-8 -*-
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This plugin allows to stop your virtual machine.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name']

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        #----------------------------------
        self.stop()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status...")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> Virtual machine is already booted")
            return True
        STREAM.debug(" -> Virtual machine is turned off")
        return False

    def stop(self):
        STREAM.info("==> Attempting to gracefull shutdown Virtual machine")
        if not self.check_vm_status():
            STREAM.info(" -> Virtual machine is already stoped")
            return
        Popen("VBoxManage controlvm %s acpipowerbutton" % self.vm_name, shell=True,
                stdout=PIPE, stderr=PIPE)
        tries = 0
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if self.vm_name not in data:
                break            
            if tries > 5:
                STREAM.info(" -> Forcing shutdown Virtual machine")
                Popen("VBoxManage controlvm %s poweroff soft" % self.vm_name, shell=True,
                      stdout=PIPE, stderr=PIPE).communicate()
                break
            tries += 1
            sleep(5)


if __name__ == "__main__":
    pass
