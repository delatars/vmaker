# -*- coding: utf-8 -*-
import os
import paramiko
from time import sleep
from subprocess import Popen, PIPE
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from vmaker.plugins.port_forwarding import get_manage_port


class Keyword(object):
    """
    This plugin allows to execute arbitrary command in VirtualMachine.
        Command must return exitcode 0 if success, otherwise Exception raised.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    credentials = credentials to connect to VirtualMachine via management_type (example: credentials = root:toor)
    execute_command = command which will be executed in VirtualMachine (example: execute_command = dnf install -y curl)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'credentials', 'execute_command']
    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None
    connections_limit = 20

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        self.execute_command = self.execute_command
        self.credentials = self.credentials
        # -------------------------------------------
        self.get_connection_settings()
        ssh = self.connect_to_vm()
        self.command_exec(ssh, self.execute_command.strip())
        self.close_ssh_connection(ssh)

    def connect_to_vm(self):
        """Method connects to VirtualMachine via ssh"""
        def try_connect(ssh):
            """Recursive function to enable multiple connection attempts"""
            self.connect_tries += 1
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
        """Method to close connection"""
        ssh.close()

    def command_exec(self, ssh, command, stdin=""):
        """Method to execute remote command via ssh connection"""
        STREAM.info(" -> Executing command: %s" % command)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write(stdin)
        ssh_stdin.flush()
        stdout = ssh_stdout.read()
        stderr = ssh_stderr.read()
        STREAM.debug(self.get_decoded(stdout))
        if len(stderr) > 0:
            STREAM.debug(self.get_decoded(stderr))
        exit_code = ssh_stdout.channel.recv_exit_status()
        STREAM.debug(" -> Command exitcode: %s" % exit_code)
        if exit_code == 0:
            STREAM.success(" -> Command executed successfully")
        else:
            raise Exception("Executed command exit status not 0")

    def get_connection_settings(self):
        """Method get connection settings from configuration file attributes"""
        self.ssh_port = get_manage_port(self.vm_name)
        if self.ssh_port is None:
            raise Exception("Manage port not specified! You need to use plugin 'port_forwarding' first.")
        try:
            user, password = self.credentials.split(":")
        except ValueError:
            raise Exception("Credentials must be in 'user:pass' format!")
        self.ssh_user = user.strip()
        self.ssh_password = password.strip()

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
        return u"Can't decode line"


if __name__ == "__main__":
    pass
