# -*- coding: utf-8 -*-
import paramiko
import requests
import re
import os
from bs4 import BeautifulSoup
from time import sleep
from subprocess import PIPE, Popen
from vmaker.init.settings import vars
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword:
    """
    This plugin allows to automatically update your virtual machines.
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'forwarding_ports', 'credentials']

    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None
    ssh_rule_name = "vm_ssh"
    vbox_url = "https://download.virtualbox.org/virtualbox/"

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        self.forwarding_ports = self.forwarding_ports
        self.credentials = self.credentials
        # -------------------------------------------
        self.uname = None
        self.get_connection_settings()
        ssh = self.connect_to_vm()
        self.detected_os = self.get_update_cmd(ssh)
        STREAM.info("==> Updating VM.")
        update_method = getattr(self, "update_%s" % self.detected_os)
        update_method(ssh)
        self.close_ssh_connection(ssh)

    def get_connection_settings(self):
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

    def get_update_cmd(self, ssh):
        known_oses = [
            "ubuntu",
            "centos",
            "fedora",
            "debian",
            "redhat",
            "suse",
            "opensuse",
            "freebsd"
        ]
        STREAM.info("==> Detecting platform")
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
                STREAM.info(" -> Detected: %s" % iter_os)
                return iter_os
        raise KeyError("Unknown os! (Not in list of 'known_oses')")

    def connect_to_vm(self):

        def try_connect(ssh):
            STREAM.info("==> Connecting to VM...")
            sleep(10)
            try:
                ssh.connect(self.ssh_server, port=int(self.ssh_port), username=self.ssh_user, password=self.ssh_password)
                STREAM.success(" -> Connection established")
            except paramiko.ssh_exception.SSHException as err:
                if self.connect_tries > 10:
                    STREAM.error(" -> Connection retries limit exceed!")
                    raise paramiko.ssh_exception.SSHException("Connection retries limit exceed!")
                self.connect_tries += 1
                STREAM.warning(" -> Fail")
                STREAM.debug(" -> %s" % err)
                STREAM.info(" -> Retry %s: Connecting to VM..." % self.connect_tries)
                try_connect(ssh)

        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect_tries = 0
        try_connect(ssh)
        del self.connect_tries
        return ssh

    def close_ssh_connection(self, connection):
        connection.close()

    def command_exec(self, ssh, command, stdin=""):
        STREAM.info(" -> Executing command: %s" % command)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write(stdin)
        ssh_stdin.flush()

        def line_buffered(f):
            while not f.channel.exit_status_ready():
                yield f.readline().strip()

        for l in line_buffered(ssh_stdout):
            STREAM.notice(l)
        err = ssh_stderr.read()
        print len(err)
        if len(err) > 0:
            STREAM.error("Command <%s> errors: <%s>" % (command, ssh_stderr.read()))

    def mount_vbox_guestadditions(self, ssh):
        STREAM.info("==> Updating VboxGuestAdditions.")
        Popen('vboxmanage storageattach %s --storagectl "IDE" --port 1 --device 0'
                        ' --type dvddrive --medium %s --forceunmount' % (self.vm_name, "emptydrive"),
                        shell=True, stdout=PIPE, stderr=PIPE).communicate()
        last_realese = self.get_vboxga_latest_realese()
        iso = self.get_vbox_guestadditions_iso(last_realese)
        if self.check_vbox_guestadditions_version(ssh) == last_realese:
            STREAM.info("VboxGuestAdditions have a latest version.")
            return

        Popen('vboxmanage storageattach %s --storagectl "IDE"'
                        ' --port 1 --device 0 --type dvddrive --medium %s' % (self.vm_name, iso),
                        shell=True, stdout=PIPE, stderr=PIPE).communicate()
        sleep(1)
        ssh.exec_command("mkdir /mnt/dvd")
        ssh.exec_command("mount -t iso9660 -o ro /dev/cdrom /mnt/dvd")

    def check_vbox_guestadditions_version(self, ssh):
        STREAM.info(" -> Checking vbox")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("modinfo vboxguest |grep -iw version| awk '{print $2}'")
        version = ssh_stdout.read()
        STREAM.debug("Guest VboxGAs version: %s" % version)
        if len(version) > 0:
            return version
        else:
            return None

    def get_vboxga_latest_realese(self):
        versions = requests.get(self.vbox_url)
        soup = BeautifulSoup(versions.content, 'html.parser')
        data = soup.find_all('a')
        data = [a.get("href") for a in data if re.match(r"\d*\.\d*\.\d*/$", a.get("href"))]
        last_release = data[-1][:-1]
        STREAM.debug("last release: %s" % last_release)
        return last_release

    def get_vbox_guestadditions_iso(self, version):
        filename = "VBoxGuestAdditions_%s.iso" % version
        download_path = os.path.join(vars.WORK_DIR, filename)
        if os.path.exists(download_path):
            return download_path
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
    def update_centos(self, ssh):
        self.command_exec(ssh, "yum clean all")
        self.command_exec(ssh, "yum update -y", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")
        # remove old kernels $ package-cleanup --oldkernels

    def update_debian(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get -y upgrade", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")

    def update_fedora(self, ssh):
        self.command_exec(ssh, "dnf update -y", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")
        # remove old kernels $ package-cleanup --oldkernels

    def update_freebsd(self, ssh):
        self.command_exec(ssh, "freebsd-update fetch --not-running-from-cron")
        self.command_exec(ssh, "freebsd-update install")
        self.command_exec(ssh, "pkg update && pkg upgrade -y")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")
        self.command_exec(ssh, "reboot")
        sleep(30)
        ssh = self.connect_to_vm()
        self.command_exec(ssh, "pkg update && pkg upgrade -y")
        self.close_ssh_connection(ssh)

    def update_opensuse(self, ssh):
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")

    def update_redhat(self, ssh):
        """Rhel"""
        self.command_exec(ssh, "yum clean all")
        self.command_exec(ssh, "yum update -y", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")

    def update_suse(self, ssh):
        """Sles"""
        self.command_exec(ssh, "zypper clean", "a\n")
        self.command_exec(ssh, "zypper refresh", "a\n")
        self.command_exec(ssh, "zypper update -y", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "ls -l /mnt/dvd/")
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")

    def update_ubuntu(self, ssh):
        self.command_exec(ssh, "dpkg --configure -a")
        self.command_exec(ssh, "apt-get update && apt-get -y upgrade", "2\n")
        self.mount_vbox_guestadditions(ssh)
        self.command_exec(ssh, "/mnt/dvd/VBoxLinuxAdditions.run")


if __name__ == "__main__":
    pass
