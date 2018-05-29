# -*- coding: utf-8 -*-
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


if __name__ == "__main__":
    pass
