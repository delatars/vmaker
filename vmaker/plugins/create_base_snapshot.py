# -*- coding: utf-8 -*-
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    template
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name']

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        #----------------------------------
        if self.check_vm_status():
            raise Exception("Unable to create base snapshot, machine is booted.")
        self.delete_base_snapshot()
        self.create_base_snapshot()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> Virtual machine is already booted")
            return True
        STREAM.debug(" -> Virtual machine is turned off")
        return False

    def create_base_snapshot(self):
        STREAM.debug("==> Create a base snapshot")
        result = Popen('VBoxManage snapshot %s take %s' % (self.vm_name, "base"),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        STREAM.debug(result)

    def delete_base_snapshot(self):
        STREAM.debug("==> Delete base snapshot.")
        result = Popen('VBoxManage snapshot %s delete %s' % (self.vm_name, "base"),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        STREAM.debug(result)
    

if __name__ == "__main__":
    pass
