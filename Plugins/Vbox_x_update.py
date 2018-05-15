# -*- coding: utf-8 -*-
import paramiko
import platform
from time import sleep
from utils.Logger import STREAM


class Keyword:
    ssh_user = "root"
    ssh_password = "root"
    ssh_server = "127.0.0.1"
    ssh_port = 2020

    def main(self):
        pass

    def get_update_cmd(self):
        update_cmds = {"centos": "yum update -y",
                       "ubuntu": "apt update && apt upgrade -y",
                       "fedora": "dnf update -y",
                       }
        update_cmd = None
        osx = platform.platform().lower()
        for key_os in update_cmds.keys():
            if key_os in osx:
                update_cmd = update_cmds[key_os]
                break
            else:
                raise KeyError("Update cmd for this os not specified")
        return update_cmd

    def connect_to_vm(self):

        def try_connect(ssh):
            STREAM.info("==> Connecting to VM...")
            try:
                ssh.connect(self.ssh_server, port=int(self.ssh_port), username=self.ssh_user, password=self.ssh_password)
                STREAM.success(" -> Connection established")
            except paramiko.ssh_exception.SSHException:
                if self.connect_tries > 5:
                    STREAM.error(" -> Retries limit exceed!")
                    raise paramiko.ssh_exception.SSHException
                self.connect_tries += 1
                STREAM.warning(" -> Fail")
                STREAM.info(" -> Retry %s: Connecting to VM..." % self.connect_tries)
                sleep(10)
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

    def command_exec(self, ssh, command):
        print "==> Executing command: %s" % command
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write("y")
        ssh_stdin.write("\n")
        ssh_stdin.flush()
        print ssh_stdout.read()


if __name__ == "__main__":
    pass
