import os, sys

class Game:
    def __init__(self, headerTitle):
        red = bytearray([80, 79, 75, 69, 77, 79, 78, 32, 82, 69, 68, 0, 0, 0, 0, 0])
        blue = bytearray([80, 79, 75, 69, 77, 79, 78, 32, 66, 76, 85, 69, 0, 0, 0, 0])
        yellow = bytearray([80, 79, 75, 69, 77, 79, 78, 32, 89, 69, 76, 76, 79, 87, 0, 128])
        self.Type = None

        self.HeaderTitle = headerTitle
        if headerTitle == red or headerTitle == blue:
            self.Home = 45
            self.Base = 46
            self.Cgb = False
            self.MaxStates = 105
            if headerTitle == red:
                self.Patch = 'red_newv2.ips'
                self.Type = 'Pokemon Red'
            else:
                self.Patch = 'blue_newv2.ips'
                self.Type = 'Pokemon Blue'
        elif headerTitle == yellow:
            self.Home = 59
            self.Base = 64
            self.Cgb = True
            self.MaxStates = 96
            self.Patch = 'yellow_newv2.ips'
            self.Type = 'Pokemon Yellow'
        else:
            raise BadGameRomException('Could not read ROM')

        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath('.')

        self.Patch = os.path.join(base_path, self.Patch)


class BadGameRomException(Exception):
    pass
