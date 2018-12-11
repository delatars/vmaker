# -*- coding: utf-8 -*-
import re
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This keyword allows to create a base snapshot (using snapshot name: 'base').
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name']

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        #----------------------------------
        if self.check_vm_status():
            raise Exception("Unable to create base snapshot, VirtualMachine is booted.")
        self.delete_base_snapshot()
        self.create_base_snapshot()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> VirtualMachine is already booted")
            return True
        STREAM.debug(" -> VirtualMachine is turned off")
        return False

    def get_snapshots_list(self):
        result = Popen('VBoxManage snapshot %s list' % self.vm_name, shell=True,
                       stdout=PIPE, stderr=PIPE).communicate()
        data = result[0].strip().split("\n")
        snapshots = {}
        for snap in data:
            try:
                name = re.findall(r'Name:\s(.*)\s\(', snap.strip())[0]
                uuid = re.findall(r'UUID:\s(.*)\)', snap.strip())[0]
                snapshots[uuid] = name
            except IndexError:
                pass
        return snapshots

    def create_base_snapshot(self):
        STREAM.info("==> Create a base snapshot")
        result = Popen('VBoxManage snapshot %s take %s' % (self.vm_name, "base"),
                       shell=True, stdout=PIPE, stderr=PIPE).communicate()
        STREAM.debug(result)
        STREAM.success(" -> Base snapshot created")

    def delete_base_snapshot(self):

        def delete_snap(uuid):
            result = Popen('VBoxManage snapshot %s delete %s' % (self.vm_name, uuid),
                           shell=True, stdout=PIPE, stderr=PIPE).communicate()
            STREAM.debug(result)

        def deletor(recursion_depth):
            snapshots = self.get_snapshots_list()
            STREAM.debug(" -> VirtualMachine snapshots: %s" % snapshots)
            if "base" not in snapshots.values():
                return
            for uuid, name in snapshots.items():
                if name == "base":
                    delete_snap(uuid)
            if recursion_depth == 0:
                return
            recursion_depth -= 1
            deletor(recursion_depth)
        STREAM.debug(" -> Delete existed base snapshots.")
        deletor(5)
    

if __name__ == "__main__":
    pass
