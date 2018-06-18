# -*- coding: utf-8 -*-
from vmaker.utils.logger import STREAM
from vmaker.utils.auxilary import exception_interceptor
from time import sleep



class Keyword(object):

    @exception_interceptor
    def main(self):
        # self.port = self.port
        # STREAM.info("Config attribute: %s " % str(self.port))
        s = 1
        while 1:
            if s > 1000:
                break
            s += 1
            sleep(1)
            if s % 10 == 0:
                STREAM.info("s = %s" % s)


if __name__ == "__main__":
    pass
