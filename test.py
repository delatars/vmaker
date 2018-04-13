class AliasObject(object):
    _type = "alias"
    common = ["start", "update"]
    
    def create_alias(self, alias, actions):
        setattr(AliasObject, alias, actions)
    
    @staticmethod
    def get_aliases():
        aliases = {}
        for attribute in AliasObject.__dict__.keys():
            if attribute[:2] != '_':
                value = getattr(AliasObject, attribute)
                if not callable(value):
                    aliases[attribute] = value
        return aliases


class GroupObject(AliasObject):
    _type = "group"
    group = None

class VmObject(GroupObject):    
    _type = "vm"    
    actions = None    
    server = "127.0.0.1"
    port = 2220
    def __init__(self):
        pass

print AliasObject.get_aliases()