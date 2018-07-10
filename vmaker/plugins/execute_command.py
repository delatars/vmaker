# -*- coding: utf-8 -*-
import os
import paramiko
from time import sleep
from subprocess import Popen, PIPE
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from vmaker.plugins.port_forwarding import get_manage_port


class Keyword(object):

    REQUIRED_CONFIG_ATTRS = ['vm_name', 'credentials', 'execute_command']
    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        self.execute_command = self.execute_command
        self.credentials = self.credentials
        # -------------------------------------------
        self.get_connection_settings()
        ssh = self.connect_to_vm()
        self.command_exec(ssh, self.execute_command.strip())
        self.close_ssh_connection(ssh)

    def connect_to_vm(self):
        """Method connects to virtual machine via ssh"""
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
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write(stdin)
        ssh_stdin.flush()
        stdout = ssh_stdout.read()
        stderr = ssh_stderr.read()
        try:
            unicode(stdout)
        except:
            stdout = stdout.decode("cp1251")
        STREAM.debug(stdout)
        if len(stderr) > 0:
            STREAM.debug(stderr)
        if ssh_stdout.channel.recv_exit_status() == 0:
            STREAM.success(" -> Command executed")
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
            raise Exception("Credentials must be in user:pass format!")
        self.ssh_user = user.strip()
        self.ssh_password = password.strip()


if __name__ == "__main__":
    pass
