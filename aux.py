# -*- coding: utf-8 -*-

class fabric:
    obj = None
    @staticmethod
    def gen_class():
        return type("vm", (fabric.obj,),{})

class VmsMetaclass(type):
    
    def __new__(cls, future_class_name, future_class_parents, future_class_attr):
        base_attrs = {name: value for name, value in future_class_attr.items() if not name.startswith('__')}
        inject_attrs = {name: getattr(fabric.gen_class(), name) for name in dir(fabric.gen_class()) if not name.startswith('__')}
        for a,b in inject_attrs.items():
            base_attrs[a]=b
        return type(future_class_name, future_class_parents, base_attrs)


if __name__=="__main__":
    pass
