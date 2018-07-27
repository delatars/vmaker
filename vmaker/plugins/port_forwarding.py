# -*- coding: utf-8 -*-
from random import randint
import re
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword:
    """
    This plugin allows to forwarding ports beetwen guest and host machines.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    forwarding_ports = label:guest:host, ... (example: forwarding_ports = manage:22:2020, icap:1344:1234)
        If 'label' = 'manage' therefore this port will be used to connect to vm.
        You can use manage:auto parameter to use automatic manage port forwarding.
    management_type = method to connect to vm (example: management_type = ssh)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'forwarding_ports', 'management_type']
    MANAGE_TYPES_DEFAULT = {"ssh": 22, "telnet": 23, "winrm": 5985}

    @exception_interceptor
    def main(self):
        # - Use Config attributes
        self.vm_name = self.vm_name
        # self.forwarding_ports input format: name:guest:host, ... ex: vm_ssh:22:2020, icap:1344:1234
        self.forwarding_ports = self.forwarding_ports
        self.management_type = self.management_type
        # ------------------------------------
        STREAM.info("==> Forwarding ports.")
        if self.check_vm_status():
            raise Exception("Unable to forwarding ports, machine is booted.")
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

    def generate_auto(self):
        name = "vmaker_manage"
        guest = self.MANAGE_TYPES_DEFAULT[self.management_type]
        host = randint(49152, 65535)
        return name, guest, host

    def forward(self):
        self.forwarding_ports = [ports.strip() for ports in self.forwarding_ports.split(",")]
        for item in self.forwarding_ports:
            ports_rule = item.split(":")
            if len(ports_rule) == 3:
                name, guest, host = ports_rule
                name, guest, host = name.strip(), guest.strip(), host.strip()
                name = "vmaker_"+name
            elif len(ports_rule) == 2:
                name, auto = ports_rule
                name, auto = name.strip(), auto.strip()
                if name == "manage" and auto == "auto":
                    name, guest, host = self.generate_auto()
                else:
                    continue
            else:
                continue
            STREAM.debug("%s, %s, %s" % (name, guest, host))
            check_name = Popen("vboxmanage showvminfo %s |grep -i %s" % (self.vm_name, name),
                               shell=True, stdout=PIPE, stderr=PIPE).communicate()
            if check_name[0] != "":
                print(name)
                STREAM.debug(" -> Detecting previosly set up rule with the same name.")
                Popen("vboxmanage modifyvm %s --natpf1 delete %s" % (self.vm_name, name),
                      shell=True, stdout=PIPE, stderr=PIPE).communicate()
                STREAM.debug(" -> Deleted rule: %s" % name)
                STREAM.debug(" -> Set up new rule: %s" % name)
                result = Popen("vboxmanage modifyvm %s --natpf1 %s,tcp,127.0.0.1,%s,,%s" %
                               (self.vm_name, name, host, guest), shell=True, stdout=PIPE, stderr=PIPE).communicate()
                STREAM.debug(result)
            else:
                check_port = Popen("vboxmanage showvminfo %s |grep -i 'host port = %s'" % (self.vm_name, host),
                                   shell=True, stdout=PIPE, stderr=PIPE).communicate()
                if check_port[0] != "":
                    raise Exception(" -> Host port(%s) already in use! Check your virtual machine settings." % host)
                result = Popen("vboxmanage modifyvm %s --natpf1 %s,tcp,127.0.0.1,%s,,%s" %
                               (self.vm_name, name, host, guest), shell=True, stdout=PIPE, stderr=PIPE).communicate()
                STREAM.debug(result)
            STREAM.success(" -> Forwarded ports %s(guest) => %s(host)" % (guest, host))


def get_manage_port(vm_name):
    """This function you can use in your plugins, to get manage port of virtual machine you need to"""
    manage_port = None
    check = Popen("vboxmanage showvminfo %s |grep -i %s" % (vm_name, "vmaker_manage"),
                  shell=True, stdout=PIPE, stderr=PIPE).communicate()
    try:
        manage_port = int(re.findall(r"host port = \d*", check[0])[0].split("=")[1].strip())
    except:
        pass
    return manage_port


if __name__ == "__main__":
    pass
