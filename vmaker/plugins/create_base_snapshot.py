# -*- coding: utf-8 -*-
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This plugin allows to create a base snapshot (using snapshot name: 'base').
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
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
        STREAM.info("==> Create a base snapshot")
        result = Popen('VBoxManage snapshot %s take %s' % (self.vm_name, "base"),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        stderr = result[1]
        if len(stderr) > 0:
            STREAM.error(stderr)
        STREAM.debug(result)
        STREAM.success(" -> Base snapshot created")

    def delete_base_snapshot(self):
        STREAM.debug(" -> Delete existed base snapshot.")
        result = Popen('VBoxManage snapshot %s delete %s' % (self.vm_name, "base"),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        stderr = result[1]
        if len(stderr) > 0:
            STREAM.error(stderr)
        STREAM.debug(result)
    

if __name__ == "__main__":
    pass
