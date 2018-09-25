# -*- coding: utf-8 -*-
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM


class _Report:
    """Object report"""
    vm_name = None
    failed_action = None
    email = None
    msg = None

    def __init__(self, vm_name, failed_action, msg, email):
        self.vm_name = vm_name
        self.failed_action = failed_action
        self.msg = msg
        self.email = email


class Reporter:
    """Class to harvest error reports and sending notifications via email"""
    CONFIG_OPTION = "alert"
    VMS = {}
    ENABLE_HARVESTER = False
    SMTP_SERVER = None
    SMTP_PORT = None
    SMTP_USER = None
    SMTP_PASS = None
    SMTP_SEND_FROM = None
    CHILD_ERR = None

    def __init__(self, vms_objects):
        """gets dict with virtual machines objects"""
        self.VMS = vms_objects
        self._get_connection_settings()
        self.reports = {}
        self.errors_counter = 0

    def _get_email(self, vm):
        """get email from virtual machine object"""
        try:
            return getattr(self.VMS[vm], self.CONFIG_OPTION)
        except AttributeError:
            return None

    def _get_connection_settings(self):
        self.SMTP_SERVER = LoadSettings.SMTP_SERVER
        self.SMTP_PORT = LoadSettings.SMTP_PORT
        self.SMTP_USER = LoadSettings.SMTP_USER
        self.SMTP_PASS = LoadSettings.SMTP_PASS
        self.SMTP_SEND_FROM = LoadSettings.SMTP_SEND_FROM
        if self.SMTP_SERVER != "":
            self.ENABLE_HARVESTER = True
            STREAM.notice("Email notifications: ON")
        else:
            STREAM.notice("Email notifications: OFF")

    def _send_report(self, emailto, subject, body, filepath=None):
        if not self.ENABLE_HARVESTER:
            return False
        fromaddr = self.SMTP_SEND_FROM
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = emailto
        msg['Subject'] = subject
        body = body
        msg.attach(MIMEText(body, 'plain'))
        if filepath is not None:
            attachment = open(filepath, "rb")
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment; filename= %s" % os.path.basename(filepath))
            msg.attach(part)
        text = msg.as_string()
        smtp = smtplib.SMTP()
        smtp.connect(self.SMTP_SERVER, self.SMTP_PORT)
        if self.SMTP_USER != "" and self.SMTP_PASS != "":
            smtp.login(self.SMTP_USER, self.SMTP_PASS)
        smtp.sendmail(fromaddr, emailto, text)
        smtp.quit()

    def add_report(self, vm, action, report):
        """add report to harvester"""
        email = self._get_email(vm)
        if self.ENABLE_HARVESTER and email is not None:
            try:
                self.reports[email] += [_Report(vm, action, report, email)]
                self.errors_counter += 1
            except KeyError:
                self.reports[email] = [_Report(vm, action, report, email)]
                self.errors_counter += 1

    def send_reports(self):
        """Sending all harvested reports"""
        STREAM.debug("There are %s error reports found" % self.errors_counter)
        for email, report in self.reports.items():
            msg = "You received this message because you are subscribed to" \
                  " vmaker notifications about VM errors.\nErrors:\n" \
                  "-------------------------------"
            for rep in report:
                msg += """
    Virtual machine:  %s
    Action:  %s\n
    Error: \n%s
-------------------------------------------------------------------\n""" % (rep.vm_name, rep.failed_action, rep.msg)
            STREAM.debug("==> Sending a report to: %s" % email)
            try:
                self._send_report(email, "vmaker:notifications:VirtualMachines:errors", msg)
                STREAM.debug(" -> OK")
            except Exception as exc:
                STREAM.debug(" -> Failed (%s)" % exc)
