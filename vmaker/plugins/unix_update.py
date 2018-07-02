# -*- coding: utf-8 -*-
import paramiko
import requests
import re
import os
import sys
from bs4 import BeautifulSoup
from time import sleep
from subprocess import PIPE, Popen
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword:
    """
    This plugin allows to automatically update your virtual machines.
    Arguments of user configuration file:
    vm_name = name of the virtual machine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    forwarding_ports = attribute of the 'port_forwarding' plugin (name:guest:host, ...)
    ssh_rule_name = name of the port_forwarding rulename to connect via ssh (example: ssh_rule_name = vm_ssh)
    credentials = credentials to connect to virtual machine via ssh (example: credentials = root:toor)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'forwarding_ports', 'credentials', 'ssh_rule_name']

    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None
    vbox_url = "https://download.virtualbox.org/virtualbox/"

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        self.forwarding_ports = self.forwarding_ports
        self.ssh_rule_name = self.ssh_rule_name
        self.credentials = self.credentials
        # -------------------------------------------
        self.uname = None
        self.get_connection_settings()
        ssh = self.connect_to_vm()
        self.detected_os = self.get_vm_platform(ssh)
        STREAM.info("==> Updating Virtual machine.")
        # Invoke update method
        update_method = getattr(self, "update_%s" % self.detected_os)
        update_method(ssh)
        self.close_ssh_connection(ssh)

    def get_connection_settings(self):
        """Method get connection settings from configuration file attributes"""
        self.forwarding_ports = [ports.strip() for ports in self.forwarding_ports.split(",")]
        for item in self.forwarding_ports:
            name, guest, host = item.split(":")
            if name == self.ssh_rule_name:
                self.ssh_port = host
        if self.ssh_port is None:
            raise Exception("Rulename '%s' not found in forwarding_ports attribute. Check your user configuration file."
                            % self.ssh_rule_name)
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

    def connect_to_vm(self):
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

    def vbox_guestadditions_update(self, ssh):
        """Method to update Virtual Box Guest Additions in virtual machine"""
        def line_buffered(f, f2):
            while not f.channel.exit_status_ready():
                yield f.readline().strip(), f2.readline().strip()

        STREAM.info("==> Updating VboxGuestAdditions.")
        if not self.mount_vbox_guestadditions(ssh):
            return
        STREAM.debug(" -> Execute update GuestAdditions.")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/mnt/dvd/VBoxLinuxAdditions.run")
        ssh_stdin.write("y\n")
        ssh_stdin.flush()
        for l, l2 in line_buffered(ssh_stdout, ssh_stderr):
            STREAM.debug(l)
            STREAM.debug(l2)
        STREAM.success(" -> VboxGuestAdditions updated")

    def mount_vbox_guestadditions(self, ssh):
        """Method to mount VirtualBoxGuestAdditions.iso to virtual machine"""
        Popen('vboxmanage storageattach %s --storagectl "IDE" --port 1 --device 0'
                        ' --type dvddrive --medium %s --forceunmount' % (self.vm_name, "emptydrive"),
                        shell=True, stdout=PIPE, stderr=PIPE).communicate()
        last_realese = self.get_vboxga_latest_realese()
        iso = self.get_vbox_guestadditions_iso(last_realese)
        if self.check_vbox_guestadditions_version(ssh) == last_realese:
            STREAM.success("VboxGuestAdditions have a latest version (%s)." % last_realese)
            return False
        Popen('vboxmanage storageattach %s --storagectl "IDE"'
                        ' --port 1 --device 0 --type dvddrive --medium %s' % (self.vm_name, iso),
                        shell=True, stdout=PIPE, stderr=PIPE).communicate()
        sleep(1)
        ssh.exec_command("mkdir /mnt/dvd")
        ssh.exec_command("mount -t iso9660 -o ro /dev/cdrom /mnt/dvd")
        sleep(1)
        return True

    def check_vbox_guestadditions_version(self, ssh):
        """Method to check version of Virtual Box Guest Additions in virtual machine"""
        STREAM.debug(" -> Checking VboxGuestAdditions version")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("modinfo vboxguest |grep -iw version| awk '{print $2}'")
        version = ssh_stdout.read()
        if len(version) > 0:
            STREAM.debug("Guest VboxGuestAdditions version: %s" % version.strip())
            return version.strip()
        else:
            STREAM.debug("Guest VboxGuestAdditions version: undefined")
            return None

    def create_base_snapshot(self):
        STREAM.info("==> Create a base snapshot")
        Popen('VBoxManage snapshot %s take %s' % (self.vm_name, "base"),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()


    def restore_from_base_snapshot(self):
        STREAM.info("==> Restore to base state")
        Popen('VBoxManage snapshot %s restore %s' % (self.vm_name, "base"),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()
        STREAM.info(" -> Restore complete.")

    def delete_base_snapshot(self, vm_name):
        STREAM.info("==> Delete base snapshot.")
        Popen('VBoxManage snapshot %s delete %s' % (vm_name, "base"),
              shell=True, stdout=sys.stdout, stderr=sys.stdout).communicate()

    def get_vboxga_latest_realese(self):
        """Method to get the last release of Virtual Box Guest Additions from Virtual Box server"""
        versions = requests.get(self.vbox_url)
        soup = BeautifulSoup(versions.content, 'html.parser')
        data = soup.find_all('a')
        data = [a.get("href") for a in data if re.match(r"\d*\.\d*\.\d*/$", a.get("href"))]
        last_release = data[-1][:-1]
        STREAM.debug("last release: %s" % last_release)
        return last_release

    def get_vbox_guestadditions_iso(self, version):
        """Method to download VirtualBoxGuestAdditions.iso from Virtual Box server"""
        filename = "VBoxGuestAdditions_%s.iso" % version
        download_path = os.path.join(LoadSettings.WORK_DIR, filename)
        if os.path.exists(download_path):
            return download_path
        Popen('rm -rf *.iso', shell=True, stdout=PIPE, stderr=PIPE).communicate()
        download_link = self.vbox_url+version+"/"+filename
        STREAM.debug("download link: %s" % download_link)
        iso = requests.get(download_link).content
        STREAM.info(" -> Downloading VboxGuestAdditions...")
        with open(download_path, "wb") as ga:
            ga.write(iso)
        STREAM.success(" -> Downloaded: %s" % download_path)
        return download_path

# Update methods.
# -----------------------------------------------------------------------------------
    def update_arch(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_altlinux(self, ssh):
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_centos(self, ssh):
        self.command_exec(ssh, "yum clean all")
        self.command_exec(ssh, "yum update -y", "2\n")
        self.vbox_guestadditions_update(ssh)
        # remove old kernels $ package-cleanup --oldkernels

    def update_debian(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_fedora(self, ssh):
        self.command_exec(ssh, "dnf update -y", "2\n")
        self.vbox_guestadditions_update(ssh)
        # remove old kernels $ package-cleanup --oldkernels

    def update_freebsd(self, ssh):
        self.command_exec(ssh, "freebsd-update fetch --not-running-from-cron")
        self.command_exec(ssh, "freebsd-update install")
        self.command_exec(ssh, "pkg update && pkg upgrade -y")
        self.vbox_guestadditions_update(ssh)
        self.command_exec(ssh, "reboot")
        sleep(30)
        ssh = self.connect_to_vm()
        self.command_exec(ssh, "pkg update && pkg upgrade -y")
        self.close_ssh_connection(ssh)

    def update_linuxmint(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get -y upgrade", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_opensuse(self, ssh):
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_redhat(self, ssh):
        """Rhel"""
        self.command_exec(ssh, "yum clean all")
        self.command_exec(ssh, "yum update -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_suse(self, ssh):
        """Sles"""
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.vbox_guestadditions_update(ssh)

    def update_ubuntu(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get upgrade -y", "2\n")
        self.command_exec(ssh, "apt-get dist-upgrade -y", "2\n")
        self.vbox_guestadditions_update(ssh)


if __name__ == "__main__":
    pass
