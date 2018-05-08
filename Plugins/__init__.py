# -*- coding: utf-8 -*-

############################################################################################
# This module provide you to write your own action keywords and use it in Actions.ini
# Requirements:
#   - Keywords must be class objects
#   - Keywords names must be started with <Keyword_> prefix example: class Keyword_my:
#   - Each Keywords must contain <main> method, it's an entrypoint of Keyword
#   - You can specify your attributes in Actions.ini and use it in your keywords
############################################################################################

#############################################
# - metaclass to build classes in that module
# - Do not delete it!

# from auxilary import VmsMetaclass
# __metaclass__ = VmsMetaclass
#############################################


############################################################################################
