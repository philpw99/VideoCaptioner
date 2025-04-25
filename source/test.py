from enum import Enum

class test(Enum):
    aaa = "aaa"
    bbb = "bbb"
    ccc = "ccc"

e = test.aaa

print (e in [test.aaa, test.bbb, test.ccc] )
