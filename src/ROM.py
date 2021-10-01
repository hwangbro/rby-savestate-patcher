from game import Game

class ROM:
    def __init__(self, path):
        self.header = bytearray()

        with open(path, 'rb') as f:
            self.contents = bytearray(f.read())

        self.header = self.contents[:0x150]

        self.header_title = self.header[308:308+16]
        self.game = Game(self.header_title)

    def header_checksum(self):
        return self.header[0x14d]

    def global_checksum(self):
        return self.header[0x14e] << 8 | self.header[0x14f]
