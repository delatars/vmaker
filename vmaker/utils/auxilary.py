# -*- coding: utf-8 -*-
import os
from time import time


def method_timer(function):
    def wrapper(self, *args, **kwargs):
        t = time()
        func = function(self, *args, **kwargs)
        res = time() - t
        print "Function spent: %s" % res
        return True
    return wrapper

def timer(function):
    def wrapper(*args, **kwargs):
        t = time()
        func = function(*args, **kwargs)
        res = time() - t
        print "Function spent: %s" % res
        return True
    return wrapper


with open(os.path.join("box.ovf"), "r") as ovf:
    ovf_file = ovf.read()
with open(os.path.join("box.ovf"), "w") as ovf:
    ovf.write(ovf_file.replace("centos6-amd64-disk001.vmdk", "box-disk.vmdk"))


if __name__ == "__main__":
    pass
