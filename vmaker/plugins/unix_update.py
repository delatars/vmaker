# -*- coding: utf-8 -*-
import paramiko
import os
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from vmaker.plugins.vbox_stop import Keyword as vbox_stop
from vmaker.plugins.vbox_start import Keyword as vbox_start
from vmaker.plugins.port_forwarding import get_manage_port


class Keyword:
    """
    This plugin allows to automatically update your virtual machines.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    forwarding_ports = attribute of the 'port_forwarding' plugin (name:guest:host, ...)
    ssh_rule_name = name of the port_forwarding rulename to connect via ssh (example: ssh_rule_name = vm_ssh)
    credentials = credentials to connect to virtual machine via ssh (example: credentials = root:toor)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'credentials', 'management_type']

    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        self.forwarding_ports = self.forwarding_ports
        self.credentials = self.credentials
        self.management_type = self.management_type
        # -------------------------------------------
        self.uname = None
        vbox_stop.vm_name = self.vm_name
        vbox_start.vm_name = self.vm_name
        STREAM.info("==> Updating Virtual machine.")
        self.get_connection_settings()
        if self.management_type == "ssh":
            ssh = self.ssh_connect_to_vm()
        else:
            raise Exception("Don't know how to connect to vm! (parameter 'management_type' not specified)")
        self.detected_os = self.get_vm_platform(ssh)
        # Invoke update method
        update_method = getattr(self, "update_%s" % self.detected_os)
        update_method(ssh)
        self.close_ssh_connection(ssh)

    def get_connection_settings(self):
        """Method get connection settings from configuration file attributes"""
        self.ssh_port = get_manage_port(self.vm_name)
        if self.ssh_port is None:
            raise Exception("Manage port not specified!")
        try:
            user, password = self.credentials.split(":")
        except ValueError:
            raise Exception("credentials must be in user:pass format!")
        self.ssh_user = user.strip()
        self.ssh_password = password.strip()

    def get_vm_platform(self, ssh):
        """Method detects platform in virtual machine"""
        known_oses = [
            "arch",
            "altlinux",
            "centos",
            "debian",
            "fedora",
            "freebsd",
            "linuxmint",
            "opensuse",
            "redhat",
            "suse",
            "ubuntu"
        ]
        STREAM.debug("==> Detecting platform")
        STREAM.debug("Known_oses: %s" % known_oses)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python -m platform")
        if len(ssh_stderr.read()) > 0:
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python2 -m platform")
            if len(ssh_stderr.read()) > 0:
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python3 -m platform")
                if len(ssh_stderr.read()) > 0:
                    raise KeyError("python not found on remote os!")
        osx = ssh_stdout.read().lower()
        self.uname = osx
        STREAM.debug(" -> Platform: %s" % osx.strip())
        for iter_os in known_oses:
            if iter_os in osx:
                STREAM.debug(" -> Detected: %s" % iter_os)
                return iter_os
        raise KeyError("Unknown os! (Not in list of 'known_oses')")

    def ssh_connect_to_vm(self):
        """Method connects to virtual machine via ssh"""
        def try_connect(ssh):
            """Recursive function to enable multiple connection attempts"""
            sleep(10)
            try:
                ssh.connect(self.ssh_server, port=int(self.ssh_port), username=self.ssh_user, password=self.ssh_password)
                STREAM.success(" -> Connection established")
            except Exception as err:
                STREAM.warning(" -> Fail (%s)" % err)
                if "ecdsakey" in str(err):
                    STREAM.warning("ECDSAKey error, try to fix.")
                    Popen('ssh-keygen -f %s -R "[%s]:%s"' %
                          (os.path.join(os.path.expanduser("~"), ".ssh/known_hosts"), self.ssh_server, self.ssh_port),
                          shell=True, stdout=PIPE, stderr=PIPE).communicate()
                if self.connect_tries > 9:
                    raise paramiko.ssh_exception.SSHException("Connection retries limit exceed!")
                self.connect_tries += 1
                STREAM.info(" -> Connection retry %s:" % self.connect_tries)
                try_connect(ssh)

        STREAM.info("==> Connecting to Virtual machine (port = %s)." % self.ssh_port)
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect_tries = 0
        try_connect(ssh)
        del self.connect_tries
        return ssh

    def close_ssh_connection(self, ssh):
        """Method to close connection"""
        ssh.close()

    def command_exec(self, ssh, command, stdin=""):
        """Method to execute remote command via ssh connection"""
        def line_buffered(f):
            """Iterator object to get output in realtime from stdout buffer"""
            while not f.channel.exit_status_ready():
                yield f.readline().strip()

        STREAM.info(" -> Executing command: %s" % command)
        # Temporarily change locale of virtual machine to en_US to prevent UnicodeDecode errors
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("export LANG=en_US.UTF-8 && %s" % command)
        ssh_stdin.write(stdin)
        ssh_stdin.flush()
        for l in line_buffered(ssh_stdout):
            STREAM.debug(l)
        err = ssh_stderr.read()
        if len(err) > 0:
            STREAM.error(err)
            raise Exception(err)

    def check_for_success_update(self):
        vbox_stop().main()
        vbox_start().main()
        ssh = self.connect_to_vm()
        self.close_ssh_connection(ssh)
        vbox_stop().main()

# Update methods.
# -----------------------------------------------------------------------------------
    def update_arch(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.check_for_success_update()

    def update_altlinux(self, ssh):
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.check_for_success_update()

    def update_centos(self, ssh):
        self.command_exec(ssh, "yum clean all")
        self.command_exec(ssh, "yum update -y", "2\n")
        self.check_for_success_update()
        # remove old kernels $ package-cleanup --oldkernels

    def update_debian(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.check_for_success_update()

    def update_fedora(self, ssh):
        self.command_exec(ssh, "dnf update -y", "2\n")
        self.check_for_success_update()
        # remove old kernels $ package-cleanup --oldkernels

    def update_freebsd(self, ssh):
        self.command_exec(ssh, "freebsd-update fetch --not-running-from-cron")
        self.command_exec(ssh, "freebsd-update install")
        self.command_exec(ssh, "pkg update && pkg upgrade -y")
        vbox_stop().main()
        vbox_start().main()
        ssh = self.connect_to_vm()
        self.command_exec(ssh, "pkg update && pkg upgrade -y")
        self.close_ssh_connection(ssh)
        self.check_for_success_update()

    def update_linuxmint(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get -y upgrade", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.check_for_success_update()

    def update_opensuse(self, ssh):
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.check_for_success_update()

    def update_redhat(self, ssh):
        """Rhel"""
        self.command_exec(ssh, "yum clean all")
        self.command_exec(ssh, "yum update -y", "2\n")
        self.check_for_success_update()

    def update_suse(self, ssh):
        """Sles"""
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.check_for_success_update()

    def update_ubuntu(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.check_for_success_update()


if __name__ == "__main__":
    pass
