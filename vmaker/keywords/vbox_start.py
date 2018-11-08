# -*- coding: utf-8 -*-
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This keyword allows to start your VirtualMachine.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name']

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        #----------------------------------
        self.start()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> VirtualMachine is booted")
            return True
        STREAM.debug(" -> VirtualMachine is turned off")
        return False

    def start(self):
        STREAM.info("==> Starting VirtualMachine...")
        if self.check_vm_status():
            STREAM.info(" -> VirtualMachine is already booted")
            return
        process = Popen("VBoxManage startvm %s --type headless" % self.vm_name, shell=True,
                        stdout=PIPE, stderr=PIPE).communicate()
        stderr = process[1]
        if len(stderr) > 0:
            raise Exception(stderr)
        while 1:
            sleep(10)
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if self.vm_name in data:
                break
        STREAM.info(" -> VirtualMachine successfully booted.")

    def clearing(self):
        STREAM.info(" -> Attempting to gracefull shutdown VirtualMachine")
        if not self.check_vm_status():
            STREAM.info(" -> VirtualMachine is already stoped")
            return
        process = Popen("VBoxManage controlvm %s acpipowerbutton" % self.vm_name, shell=True,
                        stdout=PIPE, stderr=PIPE).communicate()
        stderr = process[1]
        if len(stderr) > 0:
            raise Exception(stderr)
        tries = 0
        while 1:
            rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
            data = rvms.stdout.read()
            if self.vm_name not in data:
                break
            if tries > 5:
                STREAM.info(" -> Forcing shutdown VirtualMachine")
                Popen("VBoxManage controlvm %s poweroff soft" % self.vm_name, shell=True,
                      stdout=PIPE, stderr=PIPE).communicate()
                break
            tries += 1
            sleep(5)
    

if __name__ == "__main__":
    pass
