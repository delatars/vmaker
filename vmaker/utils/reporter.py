# -*- coding: utf-8 -*-
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM, LoggerOptions


class MailTemplate:
    """mail template"""
    VMAKER_SESSION = LoggerOptions._SESSION_ID
    ERRORS = 0

    def __init__(self):
        self.template = ""

    def add_block(self, vm_name, status, action):
        if action is not None:
            self.template += '<b>%s,</b> <b style="color:red">%s</b> ' \
                             '<b>(failed action: %s)</b><br>' % (vm_name, status, action)
        else:
            self.template += '<b>%s,</b> <b style="color:darkgreen">%s</b><br>' % (vm_name, status)

    def initialize_caption(self):
        self.template += "<b>VMaker Report (id: %s)</b><br>" % self.VMAKER_SESSION
        self.template += "=================================================<br><br>"

    def initialize_footer(self):
        self.template += "<br><br>=================================================<br>"
        self.template += "You received this message because you are subscribed to vmaker notifications.<br>"

    def generate_body(self):
        return self.template

    def generate_subject(self):
        if self.ERRORS > 0:
            return "[vmaker][notifications][VirtualMachines]: Unstable"
        else:
            return "[vmaker][notifications][VirtualMachines]: Success"


class _Report:
    """Object report"""
    vm_name = None
    failed_action = None
    email = None
    status = None

    def __init__(self, vm_name, status, failed_action, email):
        self.vm_name = vm_name
        self.failed_action = failed_action
        self.status = status
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
    SMTP_MAIL_FROM = None

    def __init__(self, vms_objects):
        """gets dict with virtual machines objects"""
        self.VMS = vms_objects
        self._get_connection_settings()
        self.mail_template = MailTemplate()
        self.reports = {}

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
        self.SMTP_MAIL_FROM = LoadSettings.SMTP_MAIL_FROM
        if self.SMTP_SERVER != "":
            self.ENABLE_HARVESTER = True
            STREAM.notice("Email notifications: ON")
        else:
            STREAM.notice("Email notifications: OFF")

    def _send_report(self, emailto, subject, body, filepath=None):
        if not self.ENABLE_HARVESTER:
            return False
        fromaddr = self.SMTP_MAIL_FROM
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = emailto
        msg['Subject'] = subject
        body = body
        msg.attach(MIMEText(body, 'html'))
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

    def add_report(self, vm, status, action=None):
        """add report to harvester"""
        email = self._get_email(vm)
        if self.ENABLE_HARVESTER and email is not None:
            if action is not None:
                self.mail_template.ERRORS += 1
            try:
                self.reports[email] += [_Report(vm, status, action, email)]
            except KeyError:
                self.reports[email] = [_Report(vm, status, action, email)]

    def send_reports(self):
        """Sending all harvested reports"""
        STREAM.debug("There are %s errors in VirtualMachines found" % self.mail_template.ERRORS)
        for email, report in self.reports.items():
            self.mail_template.initialize_caption()
            for rep in report:
                self.mail_template.add_block(rep.vm_name, rep.status, rep.failed_action)
            self.mail_template.initialize_footer()
            STREAM.debug("==> Sending a report to: %s" % email)
            try:
                self._send_report(email, self.mail_template.generate_subject(), self.mail_template.generate_body())
                STREAM.debug(" -> OK")
            except Exception as exc:
                STREAM.debug(" -> Failed (%s)" % exc)
