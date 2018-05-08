# -*- coding: utf-8 -*-
import __builtin__


class Fabric:
    obj = None

    @staticmethod
    def gen_class():
        return type("vm", (Fabric.obj, ), {})


class VmsMetaclass(type):
    def __new__(cls, name, bases, dct):
        base_attrs = {name: value for name, value in dct.items() if not name.startswith('__')}
        inject_attrs = {name: getattr(Fabric.gen_class(), name) for name in dir(Fabric.gen_class())
                        if not name.startswith('__') and name != "actions" and name != "aliases"}
        for key, value in inject_attrs.items():
            base_attrs[key] = value
        return type.__new__(cls, name, bases, base_attrs)


# class metaobject(object):
#     __metaclass__ = VmsMetaclass


# class AttributeInjector:
#     orig_object = __builtin__.object

#     def enable(classobj):
#         Fabric.obj = classobj
#         __builtin__.object = metaobject

#     def disable(classobj):
#         __builtin__.object = orig_object


if __name__ == "__main__":
    pass
