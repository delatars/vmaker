# -*- coding: utf-8 -*-
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This keyword allows to restore your VirtualMachine state from a snapshot.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    snapshot_name = name of the snapshot (example: snapshot_name = base)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'snapshot_name']

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        self.snapshot_name = self.snapshot_name
        #----------------------------------
        if self.check_vm_status():
            raise Exception("Unable to restore to snapshot, VirtualMachine is booted.")
        self.restore_from_snapshot()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> VirtualMachine is already booted")
            return True
        STREAM.debug(" -> VirtualMachine is turned off")
        return False

    def restore_from_snapshot(self):
        STREAM.info("==> Restore VirtualMachine state from snapshot: '%s'" % self.snapshot_name)
        result = Popen('VBoxManage snapshot %s restore %s' % (self.vm_name, self.snapshot_name),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        if len(result[1]) > 0:
            if "0%...10%...20%...30%...40%...50%...60%...70%...80%...90%...100%" not in result[1]:
                if "VBOX_E_OBJECT_NOT_FOUND" in result[1]:
                    raise Exception("Snapshot with name '%s' not found for this VirtualMachine" % self.snapshot_name)
                else:
                    raise Exception(result[1])
        STREAM.debug(result)
        STREAM.success(" -> Restore complete.")
    

if __name__ == "__main__":
    pass
