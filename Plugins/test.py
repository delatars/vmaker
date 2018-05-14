# -*- coding: utf-8 -*-
from time import sleep
from Logger import STREAM


class Keyword(object):
    time_to_kill = 2

    def main(self):
        STREAM.info("Config attribute: %s " % str(self.port))
        # s = 1
        # while 1:
        #     if s > 1000:
        #         break
        #     s += 1
        #     sleep(1)


if __name__ == "__main__":
    pass
