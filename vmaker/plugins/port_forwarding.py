# -*- coding: utf-8 -*-
import sys
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor

class Keyword:
    """
    This plugin allows to forwarding ports beetwen guest and host machines.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    forwarding_ports = name:guest:host, ... (example: forwarding_ports = vm_ssh:22:2020, icap:1344:1234)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'forwarding_ports']

    @exception_interceptor
    def main(self):
        # - Use Config attributes
        self.vm_name = self.vm_name
        # self.forwarding_ports input format: name:guest:host, ... ex: vm_ssh:22:2020, icap:1344:1234
        self.forwarding_ports = self.forwarding_ports
        #----------------------------------
        self.forward()

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> Virtual machine is already booted")
            return True
        STREAM.debug(" -> Virtual machine is turned off")
        return False

    def forward(self):
        STREAM.info("==> Forwarding ports.")
        if self.check_vm_status():
            STREAM.error(" -> Unable to forwarding ports, machine is booted.")
            raise Exception("Unable to forwarding ports, machine is booted.")
        self.forwarding_ports = [ports.strip() for ports in self.forwarding_ports.split(",")]
        for item in self.forwarding_ports:
            name, guest, host = item.split(":")
            STREAM.debug("%s, %s, %s" % (name, guest, host))
            check = Popen("vboxmanage showvminfo %s |grep -i %s" % (self.vm_name, name),
                          shell=True, stdout=PIPE, stderr=PIPE).communicate()
            if check[0] != "":
                STREAM.warning(" -> Detecting previosly set up rule with the same name.")
                Popen("vboxmanage modifyvm %s --natpf1 delete %s" % (self.vm_name, name),
                      shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
                STREAM.info(" -> Deleted rule: %s" % name)
                STREAM.info(" -> Set up new rule: %s" % name)
            Popen("vboxmanage modifyvm %s --natpf1 %s,tcp,127.0.0.1,%s,,%s" % (self.vm_name, name, host, guest),
                  shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
            STREAM.success(" -> Forwarded ports %s(guest) => %s(host)" % (guest, host))


if __name__ == "__main__":
    pass
