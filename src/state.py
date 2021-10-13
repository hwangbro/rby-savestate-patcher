from dataclasses import dataclass
from ArrayUtils import encode_name, decode_name

@dataclass
class State:
    cgb: bool
    name: bytearray
    vram: bytearray
    hram: bytearray
    sram1: bytearray
    sram2: bytearray
    wram: bytearray
    palette: bytearray
    bgp: bytearray
    objp: bytearray
    tail: bytearray

    def set_name(self, name: str) -> None:
        self.name = encode_name(name.strip())

    def get_name(self) -> str:
        return decode_name(self.name).strip()
