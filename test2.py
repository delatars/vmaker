from auxilary import Fabric, VmsMetaclass
import importlib
import __builtin__


class b(object):
    port = 222


orig_object = __builtin__.object

Fabric.obj = b

# class metaobject(object):
#     __metaclass__ = None


def enable():
    # *replace* object with one that uses your metaclass
    
    __builtin__.object = metaobject

def disable():
    __builtin__.object = orig_object


enable()
i = importlib.import_module("Plugins.test")
i.Keyword().main()
