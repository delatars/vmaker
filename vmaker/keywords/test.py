# -*- coding: utf-8 -*-
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from time import sleep


class Keyword(object):
    REQUIRED_CONFIG_ATTRS = []

    @exception_interceptor
    def main(self):
        STREAM.info("This is a test keyword %s")
        # print s
        # s = 1
        # while 1:
        #     if s > 100:
        #         break
        #     s += 1
        #     sleep(1)
        #     if s % 10 == 0:
        #         STREAM.info("s = %s" % s)


if __name__ == "__main__":
    pass
