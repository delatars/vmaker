# -*- coding: utf-8 -*-
from time import time
from vmaker.utils.logger import STREAM
import inspect
import sys
from traceback import format_exc


def timer(f):
    """ This wrap function needs to track time
        of functions or methods executions"""
    def method(self, *args, **kwargs):
        t = time()
        result = f(self, *args, **kwargs)
        time_spent = time() - t
        print "Method spent: %s" % time_spent
        return result

    def func(*args, **kwargs):
        t = time()
        result = f(*args, **kwargs)
        time_spent = time() - t
        print "Function spent: %s" % time_spent
        return result
    if inspect.ismethod(f):
        return method
    return func


def exception_interceptor(f):
    """ This wrap function needs to intercept exceptions
        in child processes and redirect it to logger handler"""
    def wrapper(self, *args, **kwargs):
        try:
            result = f(self, *args, **kwargs)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as exc:
            STREAM.error(exc)
            STREAM.debug(format_exc())
            sys.exit(1)
        return result
    return wrapper


if __name__ == "__main__":
    pass
