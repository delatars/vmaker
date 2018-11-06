# -*- coding: utf-8 -*-

import importlib
import sys
from time import sleep
from vmaker.utils.logger import STREAM


class KeywordController:
    """ Class controls loading keywords
        - Check keywords
        - Load keywords"""
    
    def __init__(self, keywords):
        self.enabled_keywords = keywords

    def load_keywords(self):
        lst_of_keywords = self.enabled_keywords
        STREAM.info("==> Checking and loading keywords...")
        for keyword in lst_of_keywords:
            KeywordController.check_keyword(keyword)
        loaded_keywords = {}
        for keyword in lst_of_keywords:
            loaded_keywords[keyword] = self.load_keyword(keyword)
        return loaded_keywords

    def load_keyword(self, keyword_name):
        keyword = importlib.import_module("vmaker.keywords.%s" % keyword_name)
        cls = getattr(keyword, "Keyword")
        sleep(0.1)
        return cls        

    @staticmethod
    def check_keyword(keyword_name):
        try:
            STREAM.debug(" -> Check for keyword:")
            keyword = importlib.import_module("vmaker.keywords.%s" % keyword_name)
            STREAM.debug("    %s" % keyword)
            STREAM.debug(" -> Check for a class <Keyword>:")
            cls = getattr(keyword, "Keyword")
            STREAM.debug("    %s" % cls)
            STREAM.debug(" -> Check for entrypoint <main>:")
            entry = getattr(cls, "main")
            STREAM.debug("    %s" % entry)
            STREAM.debug(" -> Check for REQUIRED_CONFIG_ATTRS:")
            entry = getattr(cls, "REQUIRED_CONFIG_ATTRS")
            STREAM.debug("    %s" % entry)
            STREAM.success(_aligner(" -> Checking and loading keyword <%s>" % keyword_name, "OK"))
        except ImportError as err:
            STREAM.warning(_aligner(" -> Checking and loading keyword <%s>" % keyword_name, "FAILED"))
            STREAM.critical("  -> %s" % err)
            sys.exit()
        except AttributeError as err:
            STREAM.warning(_aligner(" -> Checking and loading keyword <%s>" % keyword_name, "FAILED"))
            STREAM.critical("  -> %s" % err)
            sys.exit()
        finally:
            sleep(0.1)


def _aligner(line, status):
    line_width = 60
    length = len(line)
    if length > line_width:
        return line + status
    add = line_width - length
    return line + "."*add + status


if __name__ == "__main__":
    pass
