# -*- coding: utf-8 -*-
import paramiko
import requests
import re
import os
from bs4 import BeautifulSoup
from time import sleep
from subprocess import PIPE, Popen
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from vmaker.plugins.port_forwarding import get_manage_port


class Keyword:
    """
    This plugin allows to install VirtualBox Guest Additions in your VirtualMachines.
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
    vbox_url = "https://download.virtualbox.org/virtualbox/"

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        self.forwarding_ports = self.forwarding_ports
        self.credentials = self.credentials
        self.management_type = self.management_type
        # -------------------------------------------
        self.get_connection_settings()
        if self.management_type == "ssh":
            ssh = self.ssh_connect_to_vm()
        else:
            raise Exception("Don't know how to connect to vm! (parameter 'management_type' not specified)")
        self.vbox_guestadditions_update(ssh)

    def get_connection_settings(self):
        """Method get connection settings from configuration file attributes"""
        self.ssh_port = get_manage_port(self.vm_name)
        if self.ssh_port is None:
            raise Exception("Manage port not specified! You need to use plugin 'port_forwarding' first.")
        try:
            user, password = self.credentials.split(":")
        except ValueError:
            raise Exception("Credentials must be in user:pass format!")
        self.ssh_user = user.strip()
        self.ssh_password = password.strip()

    def ssh_connect_to_vm(self):
        """Method connects to VirtualMachine via ssh"""
        def try_connect(ssh):
            """Recursive function to enable multiple connection attempts"""
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
                if self.connect_tries > 20:
                    raise paramiko.ssh_exception.SSHException("Connection retries limit exceed!")
                self.connect_tries += 1
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
        """Method to close connection"""
        ssh.close()

    def vbox_guestadditions_update(self, ssh):
        """Method to update Virtual Box Guest Additions in VirtualMachine"""

        STREAM.info("==> Updating VboxGuestAdditions.")
        if not self.mount_vbox_guestadditions(ssh):
            return
        STREAM.debug(" -> Execute update GuestAdditions.")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("/mnt/dvd/VBoxLinuxAdditions.run 2>&1")
        ssh_stdin.write("y\n")
        ssh_stdin.flush()
        stdout = ssh_stdout.read()
        if "VirtualBox Guest Additions: Running kernel modules will not be replaced until the system is restarted" in stdout:
            STREAM.success(" -> VboxGuestAdditions updated")
        else:
            STREAM.error(stdout)

    def mount_vbox_guestadditions(self, ssh):
        """Method to mount VirtualBoxGuestAdditions.iso to VirtualMachine"""
        Popen('vboxmanage storageattach %s --storagectl "IDE" --port 1 --device 0'
                        ' --type dvddrive --medium %s --forceunmount' % (self.vm_name, "emptydrive"),
                        shell=True, stdout=PIPE, stderr=PIPE).communicate()
        last_realese = self.get_vboxga_latest_realese()
        iso = self.get_vbox_guestadditions_iso(last_realese)
        if self.check_vbox_guestadditions_version(ssh) == last_realese:
            STREAM.success(" -> VboxGuestAdditions have a latest version (%s)." % last_realese)
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
        """Method to check version of Virtual Box Guest Additions in VirtualMachine"""
        STREAM.debug(" -> Checking VboxGuestAdditions version")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("modinfo vboxguest |grep -iw version| awk '{print $2}'")
        version = ssh_stdout.read()
        if len(version) > 0:
            STREAM.debug(" -> Guest VboxGuestAdditions version: %s" % version.strip())
            return version.strip()
        else:
            STREAM.debug(" -> Guest VboxGuestAdditions version: undefined")
            return None

    def get_vboxga_latest_realese(self):
        """Method to get version of the last release of Virtual Box Guest Additions from Virtual Box server"""
        versions = requests.get(self.vbox_url)
        soup = BeautifulSoup(versions.content, 'html.parser')
        data = soup.find_all('a')
        data = [a.get("href") for a in data if re.match(r"\d*\.\d*\.\d*/$", a.get("href"))]
        last_release = data[-1][:-1]
        STREAM.debug(" -> last release: %s" % last_release)
        return last_release

    def get_vbox_guestadditions_iso(self, version):
        """Method to download VirtualBoxGuestAdditions.iso from Virtual Box server"""
        filename = "VBoxGuestAdditions_%s.iso" % version
        download_path = os.path.join(LoadSettings.WORK_DIR, filename)
        if os.path.exists(download_path):
            return download_path
        Popen('rm -rf %s' % os.path.join(LoadSettings.WORK_DIR, "*.iso"), shell=True, stdout=PIPE, stderr=PIPE).communicate()
        download_link = self.vbox_url+version+"/"+filename
        STREAM.debug(" -> download link: %s" % download_link)
        iso = requests.get(download_link).content
        STREAM.info(" -> Downloading VboxGuestAdditions...")
        with open(download_path, "wb") as ga:
            ga.write(iso)
        STREAM.success(" -> Downloaded: %s" % download_path)
        return download_path


if __name__ == "__main__":
    pass
