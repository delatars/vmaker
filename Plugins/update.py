# -*- coding: utf-8 -*-
import paramiko
from time import sleep


class Keyword:

    def main(self):
        pass

    def connect_to_vm(self, server, user, password):
        print "==> Connecting to VM...... ",
        server, port = server.split(":")        
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(server, port=int(port), username=user, password=password)
        except paramiko.ssh_exception.SSHException:
            print("Fail")
            print "==> Retry: Connecting to VM...... ",
            sleep(10)
            ssh.connect(server, port=int(port), username=user, password=password)
        print "OK"
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


if __name__=="__main__":
    pass
