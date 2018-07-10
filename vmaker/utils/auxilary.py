# -*- coding: utf-8 -*-
from time import time
from vmaker.utils.logger import STREAM
import inspect
import sys
from traceback import format_exc


def timer(f):
    """This wrap function needs to track time
        of functions or methods executions"""
    def method(self, *args, **kwargs):
        t = time()
        f(self, *args, **kwargs)
        res = time() - t
        print "Method spent: %s" % res
        return True

    def func(*args, **kwargs):
        t = time()
        f(*args, **kwargs)
        res = time() - t
        print "Function spent: %s" % res
        return True
    if inspect.ismethod(f):
        return method
    return func


def exception_interceptor(f):
    """This wrap function needs to intercept exceptions
        in child processes and redirect it to logger handler"""
    def wrapper(self, *args, **kwargs):
        try:
            f(self, *args, **kwargs)
        except Exception as exc:
            STREAM.error(exc)
            STREAM.debug(format_exc())
            sys.exit(1)
        return True
    return wrapper


if __name__ == "__main__":
    pass
