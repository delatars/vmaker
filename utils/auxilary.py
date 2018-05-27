# -*- coding: utf-8 -*-
import hashlib
from time import time


def method_timer(function):
    def wrapper(self, *args, **kwargs):
        t = time()
        func = function(self, *args, **kwargs)
        res = time() - t
        print "Function spent: %s" % res
        return True
    return wrapper

def timer(function):
    def wrapper(*args, **kwargs):
        t = time()
        func = function(*args, **kwargs)
        res = time() - t
        print "Function spent: %s" % res
        return True
    return wrapper


@timer
def hash_value_for_file(block_size=65536):

    sha1 = hashlib.sha1()
    with open('Fedora-Workstation.iso', 'rb') as input_file:
        while True:
        # we use the read passing the size of the block to avoid
        # heavy ram usage
            data = input_file.read(block_size)
            if not data:
                # if we don't have any more data to read, stop.
                break
        # we partially calculate the hash
            sha1.update(data)
    hash = sha1.digest()
    print hash
    return hash


@timer
def calculate_box_hash():
        with open('Fedora-Workstation.iso', 'rb') as f:
            contents = f.read()
            hash = hashlib.sha1(contents).hexdigest()
            print hash
            return hash

t1 = calculate_box_hash()
t2 = hash_value_for_file()


if __name__ == "__main__":
    pass
