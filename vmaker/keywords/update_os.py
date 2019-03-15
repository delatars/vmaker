# -*- coding: utf-8 -*-
import paramiko
import os
from time import sleep
from subprocess import PIPE, Popen
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from vmaker.keywords.vbox_stop import Keyword as vbox_stop
from vmaker.keywords.vbox_start import Keyword as vbox_start
from vmaker.keywords.port_forwarding import get_manage_port


class Keyword:
    """
    This keyword allows to automatically update your VirtualMachines.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    credentials = credentials to connect to VirtualMachine via management_type (example: credentials = root:toor)
    management_type = method to connect to vm (example: management_type = ssh)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'credentials', 'management_type']

    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None
    connections_limit = 20

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        self.forwarding_ports = self.forwarding_ports
        self.credentials = self.credentials
        self.management_type = self.management_type
        # -------------------------------------------
        # Setting attributes to invoked keywords
        vbox_stop.vm_name = self.vm_name
        vbox_start.vm_name = self.vm_name
        STREAM.info("==> Updating VirtualMachine.")
        self.get_connection_settings()
        if self.management_type == "ssh":
            ssh = self.ssh_connect_to_vm()
        else:
            raise Exception("Don't know how to connect to vm! (parameter 'management_type' has unknown value)")
        self.detected_os = self.get_vm_platform(ssh)
        # Invoke update method
        update_method = getattr(self, "update_%s" % self.detected_os)
        update_method(ssh)
        STREAM.success(" -> VirtualMachine has been updated.")

    def get_connection_settings(self):
        """ Method get connection settings from configuration file attributes """
        self.ssh_port = get_manage_port(self.vm_name)
        if self.ssh_port is None:
            raise Exception("Manage port not specified! You need to use keyword 'port_forwarding' first.")
        try:
            user, password = self.credentials.split(":")
        except ValueError:
            raise Exception("Credentials must be in user:pass format!")
        self.ssh_user = user.strip()
        self.ssh_password = password.strip()

    def get_vm_platform(self, ssh):
        """ Method detects platform in VirtualMachine """
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
            "ubuntu",
            "windows"
        ]

        def try_harder():
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("cat /etc/os-release")
            data = ssh_stdout.read()
            STREAM.debug(data)
            name = data.split("\n")[0]
            for known_os in known_oses:
                if known_os in name.lower():
                    STREAM.debug(" -> Detected: %s" % known_os)
                    return known_os
            return None

        STREAM.debug("==> Detecting platform")
        STREAM.debug(" -> Known_oses: %s" % known_oses)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python -m platform")
        if len(ssh_stderr.read()) > 0:
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python2 -m platform")
            if len(ssh_stderr.read()) > 0:
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python3 -m platform")
                if len(ssh_stderr.read()) > 0:
                    raise KeyError("python not found on remote os!")
        osx_full = ssh_stdout.read().lower()
        _osx = osx_full.split("-")
        del _osx[-1]
        osx = ""
        for _os in _osx:
            osx += _os
        STREAM.debug(" -> Platform: %s" % osx_full.strip())
        # hack to detect last opensuse versions
        if "glibc" in osx_full:
            ret = try_harder()
            if ret is not None:
                return ret
        else:
            for known_os in known_oses:
                if known_os in osx:
                    STREAM.debug(" -> Detected: %s" % known_os)
                    return known_os
        raise KeyError("Unknown os! (Not in list of 'known_oses')")

    def ssh_connect_to_vm(self):
        """ Method connects to VirtualMachine via ssh """
        def try_connect(ssh):
            """ Recursive function to enable multiple connection attempts """
            self.connect_tries += 1
            try:
                ssh.connect(self.ssh_server, port=int(self.ssh_port), username=self.ssh_user, password=self.ssh_password)
                STREAM.success(" -> Connection established")
            except Exception as err:
                STREAM.warning(" -> Fail (%s)" % err)
                if "ecdsakey" in str(err).lower():
                    STREAM.warning("ECDSAKey error, try to fix.")
                    Popen('ssh-keygen -f %s -R "[%s]:%s"' %
                          (os.path.join(os.path.expanduser("~"), ".ssh/known_hosts"), self.ssh_server, self.ssh_port),
                          shell=True, stdout=PIPE, stderr=PIPE).communicate()
                if self.connect_tries == self.connections_limit:
                    raise paramiko.ssh_exception.SSHException("Connection retries limit(%s) exceed!"
                                                              % self.connections_limit)
                STREAM.info(" -> Connection retry %s:" % self.connect_tries)
                sleep(15)
                try_connect(ssh)

        STREAM.info("==> Connecting to VirtualMachine (port = %s)." % self.ssh_port)
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect_tries = 0
        try_connect(ssh)
        del self.connect_tries
        return ssh

    def close_ssh_connection(self, ssh):
        """ Method to close connection """
        ssh.close()

    def command_exec(self, ssh, command, stdin="", get_pty=False):
        """ Method to execute remote command via ssh connection """
        def line_buffered(f):
            """ Iterator object to get output in realtime from stdout buffer """
            while not f.channel.exit_status_ready():
                yield self.get_decoded(f.readline().strip())

        STREAM.info(" -> Executing command: %s" % command)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command, get_pty=get_pty)
        ssh_stdout._set_mode("rb")
        ssh_stdin.write(stdin)
        ssh_stdin.flush()
        for l in line_buffered(ssh_stdout):
            STREAM.debug(l)
        stderr = ssh_stderr.read()
        if len(stderr) > 0:
            try:
                raise Exception(stderr)
            except UnicodeDecodeError:
                raise Exception(self.get_decoded(stderr))
        STREAM.success(" -> Command executed successfully")

    def reboot_and_connect(self, noforce=False):
        """ Reboot VirtualMachine and connect to ssh """
        if noforce:
            vbox_stop.vbox_stop_noforce = "true"
        vbox_stop().main()
        sleep(5)
        vbox_start().main()
        ssh = self.ssh_connect_to_vm()
        return ssh

    def get_decoded(self, line):
        codes = ["utf-8",
                 "cp866",
                 "cp1251",
                 "koi8-r"]
        for code in codes:
            try:
                decoded = line.decode(code)
                return decoded
            except UnicodeDecodeError:
                pass
        return u"Can't decode line! To add additional encodings go to 'get_decoded' method of update_os keyword."

# Update methods.
# -----------------------------------------------------------------------------------
    def update_arch(self, ssh):
        self.command_exec(ssh, "pacman -Syu -y", "2\n")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_altlinux(self, ssh):
        self.command_exec(ssh, "fuser -k /var/lib/dpkg/lock")
        self.command_exec(ssh, "dpkg --configure -a", get_pty=True)
        self.command_exec(ssh, "apt-get update")
        self.command_exec(ssh, "apt-get upgrade -y", get_pty=True)
        self.command_exec(ssh, "apt-get autoremove -y", get_pty=True)
        self.command_exec(ssh, "apt-get clean")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_centos(self, ssh):
        self.command_exec(ssh, "yum update -y", "2\n")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)
        # remove old kernels $ package-cleanup --oldkernels

    def update_debian(self, ssh):
        self.command_exec(ssh, "fuser -k /var/lib/dpkg/lock")
        self.command_exec(ssh, "dpkg --configure -a", get_pty=True)
        self.command_exec(ssh, "apt-get update")
        self.command_exec(ssh, "export DEBIAN_FRONTEND=noninteractive; apt-get upgrade -y", get_pty=True)
        self.command_exec(ssh, "apt-get autoremove -y", get_pty=True)
        self.command_exec(ssh, "apt-get clean")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_fedora(self, ssh):
        self.command_exec(ssh, "dnf update -y", "2\n")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)
        # remove old kernels $ package-cleanup --oldkernels

    def update_freebsd(self, ssh):
        self.command_exec(ssh, "export IGNORE_OSVERSION=yes; pkg update", "y\n")
        self.command_exec(ssh, "pkg upgrade -y")
        ssh = self.reboot_and_connect()
        self.close_ssh_connection(ssh)

    def update_linuxmint(self, ssh):
        self.command_exec(ssh, "fuser -k /var/lib/dpkg/lock")
        self.command_exec(ssh, "dpkg --configure -a", get_pty=True)
        self.command_exec(ssh, "apt-get update")
        self.command_exec(ssh, "export DEBIAN_FRONTEND=noninteractive; apt-get upgrade -y", get_pty=True)
        self.command_exec(ssh, "apt-get autoremove -y", get_pty=True)
        self.command_exec(ssh, "apt-get clean")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_opensuse(self, ssh):
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_redhat(self, ssh):
        """ Rhel """
        self.command_exec(ssh, "yum update -y")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_suse(self, ssh):
        """ Sles """
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_ubuntu(self, ssh):
        self.command_exec(ssh, "fuser -k /var/lib/dpkg/lock")
        self.command_exec(ssh, "dpkg --configure -a", get_pty=True)
        self.command_exec(ssh, "apt-get update")
        self.command_exec(ssh, "export DEBIAN_FRONTEND=noninteractive; apt-get upgrade -y", get_pty=True)
        self.command_exec(ssh, "apt-get autoremove -y", get_pty=True)
        self.command_exec(ssh, "apt-get clean")
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        ssh = self.reboot_and_connect()
        self.command_exec(ssh, "depmod > /dev/null 2>&1")
        self.close_ssh_connection(ssh)

    def update_windows(self, ssh):
        """ Using PSWindowsUpdate module to search&install Windows Updates
        Use PsExec from SysinternalsSuite to evaluate privileges to SYSTEM (must have for Get-WUInstall) """
        PsExec = '"C:\Program Files\SysinternalsSuite\PsExec.exe" -s -i Powershell.exe '
        self.command_exec(ssh, PsExec + r'"New-Item -Path C:\Update_Log\$(get-date -f dd-MM-yyy)\ -ItemType directory -Force" 2>&1')
        self.command_exec(ssh, PsExec + r'"Get-WindowsUpdate -Install -AcceptAll -IgnoreReboot >>C:\Update_Log\$(get-date -f dd-MM-yyy)\updatelistlog.log" 2>&1')
        self.command_exec(ssh, 'shutdown -s -f -t 5')
        ssh = self.reboot_and_connect(noforce=True)
        self.command_exec(ssh, PsExec + r'"Get-WindowsUpdate -Install -AcceptAll -IgnoreReboot >>C:\Update_Log\$(get-date -f dd-MM-yyy)\updatelistlog.log" 2>&1')
        self.command_exec(ssh, PsExec + r'"Get-WUHistory -MaxDate $(Get-Date -f d) >>C:\Update_Log\$(get-date -f dd-MM-yyy)\updatelog.log" 2>&1')
        self.command_exec(ssh, PsExec + r'"Move-Item -path "C:\Update_Log\$(get-date -f dd-MM-yyy)" '
        r'-destination \\testlab-node1.i.drweb.ru\testlab-e-reports\WU_Logs\$([System.Net.Dns]::GetHostName())\ -Force" 2>&1')
        self.command_exec(ssh, r'Powershell.exe "Remove-Item C:\Update_Log\ -Recurse -Force" 2>&1')
        self.command_exec(ssh, 'shutdown -s -f -t 5')
        self.close_ssh_connection(ssh)


if __name__ == "__main__":
    pass
