import os, sys


class Game:
    def __init__(self, header_title: bytearray) -> None:
        red = bytearray([80, 79, 75, 69, 77, 79, 78, 32, 82, 69, 68, 0, 0, 0, 0, 0])
        blue = bytearray([80, 79, 75, 69, 77, 79, 78, 32, 66, 76, 85, 69, 0, 0, 0, 0])
        yellow = bytearray(
            [80, 79, 75, 69, 77, 79, 78, 32, 89, 69, 76, 76, 79, 87, 0, 128]
        )
        self.Type = None

        self.header_title = header_title
        if header_title == red or header_title == blue:
            self.home = 45
            self.base = 46
            self.cgb = False
            self.max_states = 105
            if header_title == red:
                self.patch = "red_newv2.ips"
                self.type = "Pokemon Red"
            else:
                self.patch = "blue_newv2.ips"
                self.type = "Pokemon Blue"
        elif header_title == yellow:
            self.home = 59
            self.base = 64
            self.cgb = True
            self.max_states = 96
            self.patch = "yellow_newv2.ips"
            self.type = "Pokemon Yellow"
        else:
            raise BadGameRomException("Could not read ROM")

        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        self.patch = os.path.join(base_path, self.patch)


class BadGameRomException(Exception):
    pass
