# -*- coding: utf-8 -*-
import os
import paramiko
from time import sleep
from subprocess import Popen, PIPE
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword(object):

    REQUIRED_CONFIG_ATTRS = ['forwarding_ports', 'credentials', 'ssh_rule_name']
    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        self.execute_command = self.execute_command
        self.forwarding_ports = self.forwarding_ports
        self.ssh_rule_name = self.ssh_rule_name
        self.credentials = self.credentials
        # -------------------------------------------
        if not self.check_vm_status():
            STREAM.error("==> Unable to execute command, virtual machine is turned off!")
            return
        self.get_connection_settings()
        ssh = self.connect_to_vm()
        self.command_exec(ssh, self.execute_command.strip())
        self.close_ssh_connection(ssh)

    def check_vm_status(self):
        STREAM.debug("==> Check Vm status.")
        rvms = Popen("VBoxManage list runningvms | awk '{print $1}'", shell=True, stdout=PIPE, stderr=PIPE)
        data = rvms.stdout.read()
        if self.vm_name in data:
            STREAM.debug(" -> Virtual machine is already booted")
            return True
        STREAM.debug(" -> Virtual machine is turned off")
        return False

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
        STREAM.info(" -> Executing command: %s" % command)
        # Temporarily change locale of virtual machine to en_US to prevent UnicodeDecode errors
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("export LANG=en_US.UTF-8 && %s" % command)
        ssh_stdin.write(stdin)
        ssh_stdin.flush()
        STREAM.notice(ssh_stdout.read())
        err = ssh_stderr.read()
        if len(err) > 0:
            STREAM.error(err)

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


if __name__ == "__main__":
    pass
