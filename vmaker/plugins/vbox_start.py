# -*- coding: utf-8 -*-
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This plugin allows to start your virtual machine.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name']

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        #----------------------------------
        self.start()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> Virtual machine is already booted")
            return True
        STREAM.debug(" -> Virtual machine is turned off")
        return False

    def start(self):
        STREAM.info("==> Starting Virtual machine...")
        if self.check_vm_status():
            STREAM.info(" -> Virtual machine is already booted")
            return
        process = Popen("VBoxManage startvm %s --type headless" % self.vm_name, shell=True,
                        stdout=PIPE, stderr=PIPE).communicate()
        stderr = process[1]
        if len(stderr) > 0:
            STREAM.error(stderr)
            raise Exception(stderr)
        while 1:
            sleep(10)
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if self.vm_name in data:
                break
        STREAM.info(" -> Virtual machine successfully booted.")
    

if __name__ == "__main__":
    pass
