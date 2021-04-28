from ArrayUtils import *
from game import *

class ROM:
    def __init__(self, path):
        self.Data = bytearray()
        self.Header = bytearray()

        BankSize = 0x4000

        with open(path, 'rb') as f:
            self.Contents = bytearray(f.read())

        self.Header = self.Contents[:0x150]

        self.HeaderTitle = self.Header[308:308+16]
        self.Game = Game(self.HeaderTitle)

    def header_checksum(self):
        return self.Header[0x14d]

    def global_checksum(self):
        return self.Header[0x14e] << 8 | self.Header[0x14f]
