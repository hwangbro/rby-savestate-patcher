from ArrayUtils import *
from ips_util import Patch as PatchIPS
from state import State


class Patch:
    def __init__(self, rom, states: dict[int, State] = None):
        self.base_rom = rom
        self.game = self.base_rom.game
        self.ips_patch = PatchIPS.load(self.game.patch)
        self.rom = None

        # dictionary of states, key is index, value is state namedtuple
        if states is None:
            states = dict()
        self.states = states

    def extract_all_states(self, rom_file_path: str) -> None:
        """Extract all relevant state data from a savestate rom."""
        with open(rom_file_path, "rb") as f:
            rom = f.read()
        num_states = (len(rom) - self.game.base * 16384) // 32768
        index = 0
        for i in range(num_states):
            state = self.extract_state(rom, i)
            if len(array_trim(state.wram)) != 0:
                self.states[index] = state
                index += 1

    def extract_state(self, rom: bytearray, index: int) -> State:
        """Extract a single state data from the ROM at a given index."""
        base = self.game.base
        home = self.game.home
        bank1 = base + index * 2
        bank2 = bank1 + 1

        vram = rom[to_full(bank1, 20480) : to_full(bank1, 20480) + 8192]
        hram = rom[to_full(bank1, 30720) : to_full(bank1, 30720) + 256]
        sram1 = rom[to_full(bank1, 31336) : to_full(bank1, 31336) + 1432]
        sram2 = rom[to_full(bank2, 20596) : to_full(bank2, 20596) + 3980]
        wram = rom[to_full(bank2, 24576) : to_full(bank2, 24576) + 8192]
        palette = bytearray(2048)
        bgp = bytearray(64)
        objp = bytearray(64)
        if self.game.cgb:
            palette = rom[to_full(bank1, 28672) : to_full(bank1, 28672) + 2048]
            bgp = rom[to_full(bank1, 30976) : to_full(bank1, 30976) + 64]
            objp = rom[to_full(bank1, 30140) : to_full(bank1, 30140) + 64]
        # tail can be variable length, set to 200 for now
        tail = rom[to_full(bank2, 0x40BC) : to_full(bank2, 0x40BC) + 200]
        name = rom[
            to_full(home, 28672) + index * 18 : to_full(home, 28672) + index * 18 + 18
        ]

        return State(
            self.game.cgb,
            name,
            vram,
            hram,
            sram1,
            sram2,
            wram,
            palette,
            bgp,
            objp,
            tail,
        )

    # states = dictionary, key = index, value = state obj
    def inject_all_states(self) -> None:
        """Inject the states from self.states into self.rom."""
        self.rom = self.ips_patch.apply(self.base_rom.contents)
        self.rom = pad_array(self.rom, self.game.base + len(self.states) * 2)

        for i in range(len(self.states)):
            self.inject_state(self.states[i], i)

        self.write_checksum()

    def inject_state(self, state: State, index: int) -> None:
        """Inject a single state into self.rom at a given index."""
        base = self.game.base
        home = self.game.home
        bank1 = base + index * 2
        bank2 = bank1 + 1

        array_copy(
            self.rom, to_full(home, 16384), self.rom, to_full(bank1, 16384), 4096
        )
        array_copy(
            self.rom, to_full(home, 16384), self.rom, to_full(bank2, 16384), 4096
        )
        array_copy(state.vram, 0, self.rom, to_full(bank1, 20480))
        array_copy(state.hram, 0, self.rom, to_full(bank1, 30720))
        array_copy(state.sram1, 0, self.rom, to_full(bank1, 31336))
        array_copy(state.sram2, 0, self.rom, to_full(bank2, 20596))
        array_copy(state.wram, 0, self.rom, to_full(bank2, 24576))
        if self.game.cgb:
            array_copy(state.palette, 0, self.rom, to_full(bank1, 28672))
            array_copy(state.bgp, 0, self.rom, to_full(bank1, 30976))
            array_copy(state.objp, 0, self.rom, to_full(bank1, 31040))

        array_copy(state.tail, 0, self.rom, to_full(bank2, 0x40BC))
        array_copy(state.name, 0, self.rom, to_full(home, 28672) + index * 18)

        self.rom[to_full(bank1, 0x408B)] = bank2 & 0xFF

    def write_checksum(self) -> None:
        """Write the two checksum bytes into the rom."""
        header = -1 * sum(self.rom[308:333]) - (333 - 308)
        self.rom[333] = header & 0xFF

        glob = sum(
            [x & 0xFF for idx, x in enumerate(self.rom) if idx != 334 and idx != 335]
        )

        self.rom[334] = glob >> 8 & 0xFF
        self.rom[335] = glob & 0xFF


def get_state_offsets(state: bytearray) -> dict[str, int]:
    """Return a dictionary with state labels and offsets."""
    save_state_labels = dict()
    offset = 3
    size = read_int_be(state[offset : offset + 3])
    offset += size + 3

    while offset < len(state):
        key_size = state.index(0, offset) - offset
        key = bytearray(key_size)
        array_copy(state, offset, key, 0, key_size)
        offset += key_size + 1
        size = read_int_be(state[offset : offset + 3])
        offset += 3
        key_string = "".join([chr(c) for c in key])
        save_state_labels[key_string] = (offset, size)
        offset += size

    return save_state_labels


def extract_state_data(state: bytearray, labels: list[str]) -> dict[str, bytearray]:
    """Return a dictionary with state labels and the relevant state data."""
    state_offsets = get_state_offsets(state)
    hashes = dict()

    for key in labels:
        index = state_offsets[key][0]
        size = state_offsets[key][1]
        hashes[key] = bytearray(state[index : index + size])

    return hashes


def make_state(state_name: str, gsr_state: bytearray, cgb: bool) -> State:
    """Return a State object with the name encoded."""
    with open(gsr_state, "rb") as f:
        gsrState = f.read()
    data = extract_state_data(
        gsrState,
        [
            "vram",
            "sram",
            "wram",
            "hram",
            "pc",
            "sp",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "h",
            "l",
            "vcycles",
            "cc",
            "ldivup",
            "bgp",
            "objp",
        ],
    )

    if read_int_be(data["pc"]) != 64:
        print("!")

    sp = read_int_be(data["sp"])
    ret = read_int_le(data["wram"][sp - 49152 : sp - 49152 + 2])
    vcycles = read_int_be(data["vcycles"])
    cc = read_int_be(data["cc"])
    ldivup = read_int_be(data["ldivup"])

    div = cc & 0xFFFF

    # backwards compat
    if data["hram"][260]:
        div = data["hram"][260] * 256 + cc - ldivup

    data["hram"][320] = data["hram"][320] & 0x7F
    data["hram"][341] = 0

    vram = data["vram"][:8192]
    hram = data["hram"][256:512]
    sram1 = data["sram"][:1432]
    sram2 = data["sram"][9624 : 9624 + 3980]
    wram = data["wram"][:8192]
    palette = bytearray(2048)
    bgp = bytearray(64)
    objp = bytearray(64)

    if cgb:
        palette = data["vram"][14336 : 14336 + 2048]
        bgp = data["bgp"][:64]
        objp = data["objp"][:64]

    p2 = div
    if p2 < 132:
        p2 += 65536
    p1 = vcycles - p2
    p1 -= 16
    p2 -= 132

    lcd = bytearray([240, 64, 203, 255, 224, 64])
    delay1 = delay_cycles(p1)
    rdiv = bytearray([175, 224, 4])
    delay2 = delay_cycles(p2)

    sp2 = sp + 2

    regs = bytearray([49, sp2 & 0xFF, (sp2 >> 8) & 0xFF, 1])
    regs.extend(data["f"])
    regs.extend(data["a"])
    regs.extend([197, 241, 1])
    regs.extend(data["c"])
    regs.extend(data["b"])
    regs.append(17)
    regs.extend(data["e"])
    regs.extend(data["d"])
    regs.append(33)
    regs.extend(data["l"])
    regs.extend(data["h"])
    regs.append(251)
    regs.append(195)
    regs.extend([ret & 0xFF, (ret >> 8) & 0xFF])

    tail = bytearray(lcd + delay1 + rdiv + delay2 + regs)
    name = encode_name(state_name)

    return State(cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail)
