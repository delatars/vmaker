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
            raise Exception("Unable to restore to base snapshot, machine is booted.")
        self.restore_from_base_snapshot()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> Virtual machine is already booted")
            return True
        STREAM.debug(" -> Virtual machine is turned off")
        return False

    def restore_from_base_snapshot(self):
        STREAM.info("==> Restore to base state")
        result = Popen('VBoxManage snapshot %s restore %s' % (self.vm_name, "base"),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        if "VBOX_E_OBJECT_NOT_FOUND" in result[1]:
            raise Exception("base snapshot not found")
        STREAM.debug(result)
        STREAM.success(" -> Restore complete.")
    

if __name__ == "__main__":
    pass
