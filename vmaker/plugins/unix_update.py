# -*- coding: utf-8 -*-
import paramiko
import platform
from time import sleep
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword:
    ssh_user = "root"
    ssh_password = "root"
    ssh_server = "localhost"
    ssh_port = 2030

    @exception_interceptor
    def main(self):
        # - Config attributes
        self.vm_name = self.vm_name
        #----------------------------------
        ssh = self.connect_to_vm()
        cmd = self.get_update_cmd(ssh)
        self.command_exec(ssh, cmd, "2\n")
        self.close_ssh_connection(ssh)

    def get_update_cmd(self, ssh):
        update_cmds = {"ubuntu": "dpkg --configure -a && apt-get update && apt-get -y upgrade",
                       "centos": "yum update -y",
                       "fedora": "dnf update -y",
                       "debian": "apt update && apt upgrade -y",
                       "rhel": "yum update -y",
                       "sles": "zypper refresh && zypper update -y",
                       "opensuse": "zypper refresh && zypper update -y"
                       }
        update_cmd = None
        STREAM.info("==> Detecting platform")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("python -m platform")
        osx = ssh_stdout.read().lower()
        for key_os in update_cmds.keys():
            if key_os in osx:
                STREAM.info(" -> Detected: %s" % key_os)
                STREAM.debug(" -> Platform: %s" % osx.strip())
                update_cmd = update_cmds[key_os]
                return update_cmd
        raise KeyError("Update cmd for this os not specified")

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
        STREAM.info("==> Executing command: %s" % command)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        ssh_stdin.write(stdin)
        ssh_stdin.flush()

        def line_buffered(f):
            while not f.channel.exit_status_ready():
                yield f.readline().strip()

        for l in line_buffered(ssh_stdout):
            print l
        print "Errors: %s" % ssh_stderr.read()


if __name__ == "__main__":
    pass
