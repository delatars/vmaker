# -*- coding: utf-8 -*-
import os
import paramiko
from scp import SCPClient
from time import sleep
from subprocess import Popen, PIPE
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from vmaker.keywords.port_forwarding import get_manage_port


class Keyword(object):
    """
    This keyword allows to execute local script in VirtualMachine.
        Script must return exitcode 0 if success, otherwise Exception raised.
    Arguments of user configuration file:
    vm_name = name of the VirtualMachine in Virtual Box (example: vm_name = ubuntu1610-amd64)
    credentials = credentials to connect to VirtualMachine via management_type (example: credentials = root:toor)
    execute_script = local script which will be executed in VirtualMachine
        (example: execute_script = /home/user/script.sh # uses the default shell
         example: execute_script = python:/home/user/myscript.py
         example: execute_script = /usr/bin/python3:/home/user/myscript.py)
    """
    REQUIRED_CONFIG_ATTRS = ['vm_name', 'credentials', 'execute_script']
    ssh_server = "localhost"
    ssh_port = None
    ssh_user = None
    ssh_password = None
    connections_limit = 20

    @exception_interceptor
    def main(self):
        # - Attributes taken from config
        self.vm_name = self.vm_name
        self.execute_script = self.execute_script
        self.credentials = self.credentials
        # -------------------------------------------
        self.get_connection_settings()
        ssh = self.connect_to_vm()
        self.upload_script_and_execute(ssh, self.execute_script)
        self.close_ssh_connection(ssh)

    def connect_to_vm(self):
        """ Method connects to VirtualMachine via ssh """
        def try_connect(ssh):
            """ Recursive function to enable multiple connection attempts """
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
        """ Method to close connection """
        ssh.close()

    def upload_script_and_execute(self, ssh, parameter):
        Platform = self.get_platform(ssh)
        if parameter.strip().startswith("script:"):
            parameter = parameter[7:]
        try:
            shell, filepath = parameter.strip().split(":")
        except ValueError:
            shell = None
            filepath = parameter.strip()
        STREAM.info(" -> Executing script: %s" % filepath)
        if Platform == "win-like":
            STREAM.debug(" -> Remote system probably is windows type")
            temppath = os.path.join("C:\Windows\Temp", os.path.basename(filepath))
            default_shell = r"C:\Windows\System32\cmd.exe /c start"
        else:
            STREAM.debug(" -> Remote system probably is unix type")
            temppath = os.path.join("/tmp", os.path.basename(filepath))
            default_shell = "bash"
        if shell is None:
            STREAM.debug(" -> Shell is not specified, using default: %s" % default_shell)
            shell = default_shell
        scp = SCPClient(ssh.get_transport())
        scp.put(filepath, temppath)
        scp.close()
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("%s %s" % (shell, temppath))
        stdout = ssh_stdout.read()
        stderr = ssh_stderr.read()
        STREAM.debug(self.get_decoded(stdout))
        if len(stderr) > 0:
            STREAM.debug(self.get_decoded(stderr))
        exit_code = ssh_stdout.channel.recv_exit_status()
        STREAM.debug(" -> Script exitcode: %s" % exit_code)
        if exit_code == 0:
            STREAM.success(" -> Script executed successfully")
        else:
            raise Exception("Executed script exit status not 0")

    def get_platform(self, ssh):
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("systeminfo /?")
        exit_code = ssh_stdout.channel.recv_exit_status()
        if exit_code == 0:
            return "win-like"
        else:
            return "unix-like"

    def get_connection_settings(self):
        """ Method get connection settings from configuration file attributes """
        self.ssh_port = get_manage_port(self.vm_name)
        if self.ssh_port is None:
            raise Exception("Manage port not specified! You need to use keyword 'port_forwarding' first.")
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
