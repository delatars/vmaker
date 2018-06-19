# -*- coding: utf-8 -*-
from keystoneauth1 import loading, session
from glanceclient import Client
from ConfigParser import ConfigParser
from vmaker.init.settings import vars
import os
import sys
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor


class Keyword(object):
    REQUIRED_CONFIG_ATTRS = []

    @exception_interceptor
    def main(self):
        self.openstack_cluster = "./cluster.ini::openstack_cluster1"

        self.clusters = {}
        target_cluster = self.openstack_credentials_harvester()
        glance = self.cluster_connect(target_cluster)
        self.get_images(glance)
        # self.upload_image(glance)
        # self.delete_image("6737641a-f35d-4fe6-acdf-f2e2569c30cc")

    def openstack_credentials_harvester(self):
        STREAM.info("==> Get Openstack cluster connection settings")
        try:
            configfile, section = self.openstack_cluster.split("::")
            STREAM.debug(" -> Using user configuration file %s" % configfile)
        except ValueError:
            configfile = vars.GENERAL_CONFIG
            STREAM.debug(" -> Using general configuration file %s" % configfile)
            section = self.openstack_cluster
        config = ConfigParser()
        config.read(configfile)
        for sec in config.sections():
            if "openstack_cluster" in sec:
                args = {key: value.strip() for key, value in config.items(sec)}
                self.clusters[sec] = args
        if self.clusters == {}:
            STREAM.error(" -> There are no settings for the Openstack cluster found!")
            STREAM.error(" -> Export passed.")
            sys.exit(0)
        STREAM.info(" -> Found settings for %s Openstack clusters" % len(self.clusters))
        STREAM.info(" -> Target Openstack cluster set to: %s" % section)
        return section

    def cluster_connect(self, target_cluster):
        cluster = self.clusters[target_cluster]
        os.environ["REQUESTS_CA_BUNDLE"] = cluster["ca_cert"]
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=cluster["auth_url"],
            username=cluster["username"],
            password=cluster["password"],
            project_name=cluster["project_name"],
            user_domain_id=cluster["user_domain_id"],
            project_domain_id=cluster["project_domain_id"])
        sess = session.Session(auth=auth)
        glance = Client('2', session=sess)
        return glance

    def delete_image(self, connection, id):
        connection.images.delete(id)

    def upload_image(self, connection):
        STREAM.info("==> Uploading image.")
        image = connection.images.create(name="TestImage", disk_format="vdi", container_format="bare",
                                          is_public="True", visibility="public")
        connection.images.upload(image.id, open('./centos6-amd64.vdi', 'rb'))
        STREAM.success(" -> Uploading complete.")

    def get_images(self, connection):
        images = connection.images.list()
        for im in images:
            print im


if __name__ == "__main__":
    Keyword().main()
