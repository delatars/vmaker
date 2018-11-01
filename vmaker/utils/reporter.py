# -*- coding: utf-8 -*-
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from vmaker.init.settings import LoadSettings
from vmaker.utils.logger import STREAM, LoggerOptions
from hashlib import md5


class MailTemplate:
    """ Mail template """
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
        self.template += "https://github.com/delatars/vmaker<br>"

    def generate_body(self):
        return self.template

    def generate_subject(self, description):
        if self.ERRORS > 0:
            return "[vmaker][%s]: Unstable" % description if description is not None else "[vmaker]: Unstable"
        else:
            return "[vmaker][%s]: Success" % description if description is not None else "[vmaker]: Success"


class _Report:
    """ Object report """
    vm_name = None
    failed_action = None
    email = None
    status = None

    def __init__(self, vm_name, status, failed_action, email, description):
        self.vm_name = vm_name
        self.failed_action = failed_action
        self.status = status
        self.email = email
        self.description = description


class Reporter:
    """ Class to harvest error reports and sending notifications via email """
    CONFIG_OPTION = "alert"
    DESCRIPTION_OPTION = "alert_description"
    VMS = {}
    ENABLE_HARVESTER = False
    SMTP_SERVER = None
    SMTP_PORT = None
    SMTP_USER = None
    SMTP_PASS = None
    SMTP_MAIL_FROM = None

    def __init__(self, vms_objects):
        """ Gets dict with virtual machines objects """
        self.VMS = vms_objects
        self._get_connection_settings()
        self.mail_template = MailTemplate()
        self.reports = {}

    def _get_email(self, vm):
        """ Get email from virtual machine object """
        try:
            return getattr(self.VMS[vm], self.CONFIG_OPTION)
        except AttributeError:
            return None

    def _get_description(self, vm):
        """ Get email from virtual machine object """
        try:
            return getattr(self.VMS[vm], self.DESCRIPTION_OPTION)
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
        rcpts = [rcpt.strip() for rcpt in emailto.strip().split(",")]
        smtp = smtplib.SMTP()
        smtp.connect(self.SMTP_SERVER, self.SMTP_PORT)
        if self.SMTP_USER != "" and self.SMTP_PASS != "":
            smtp.login(self.SMTP_USER, self.SMTP_PASS)
        smtp.sendmail(fromaddr, rcpts, text)
        smtp.quit()

    def add_report(self, vm, status, action=None):
        """ Add report to harvester """
        email = self._get_email(vm)
        description = self._get_description(vm)
        if action is not None:
            self.mail_template.ERRORS += 1
        if self.ENABLE_HARVESTER and email is not None:
            if description is None:
                mail_uid = md5(email).hexdigest()
            else:
                mail_uid = md5(email+description).hexdigest()
            try:
                self.reports[mail_uid] += [_Report(vm, status, action, email, description)]
            except KeyError:
                self.reports[mail_uid] = [_Report(vm, status, action, email, description)]

    def send_reports(self):
        """ Sending all harvested reports """
        STREAM.debug("There are %s error(s) in VirtualMachines found." % self.mail_template.ERRORS)
        for mail_uid, report in self.reports.items():
            self.mail_template.initialize_caption()
            email = report[0].email
            desc = report[0].description
            for rep in report:
                self.mail_template.add_block(rep.vm_name, rep.status, rep.failed_action)
            self.mail_template.initialize_footer()
            STREAM.debug("==> Sending a report to: %s" % email)
            try:
                self._send_report(email, self.mail_template.generate_subject(desc), self.mail_template.generate_body())
                STREAM.debug(" -> OK")
            except Exception as exc:
                STREAM.debug(" -> Failed (%s)" % exc)
