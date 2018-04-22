# -*- coding: utf-8 -*-

class fabric:
    obj = None
    @staticmethod
    def gen_class():
        return type("vm", (fabric.obj,),{})

class VmsMetaclass(type):
    
    def __new__(cls, name, bases, dct):
        base_attrs = {name: value for name, value in dct.items() if not name.startswith('__')}
        inject_attrs = {name: getattr(fabric.gen_class(), name) for name in dir(fabric.gen_class()) if not name.startswith('__')}
        for key, value in inject_attrs.items():
            base_attrs[key]=value
        return type.__new__(cls, name, bases, base_attrs)


if __name__=="__main__":
    pass
