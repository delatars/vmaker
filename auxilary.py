# -*- coding: utf-8 -*-


class Fabric:
    obj = None

    @staticmethod
    def gen_class():
        return type("vm", (Fabric.obj,),{})


class VmsMetaclass(type):
    def __new__(cls, name, bases, dct):
        base_attrs = {name: value for name, value in dct.items() if not name.startswith('__')}
        inject_attrs = {name: getattr(Fabric.gen_class(), name) for name in dir(Fabric.gen_class())
                        if not name.startswith('__') and name != "actions" and name != "aliases"}
        for key, value in inject_attrs.items():
            base_attrs[key] = value
        return type.__new__(cls, name, bases, base_attrs)


if __name__ == "__main__":
    pass
