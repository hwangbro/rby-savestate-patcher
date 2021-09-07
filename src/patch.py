from ArrayUtils import *
from game import *
from ips_util import Patch as PatchIPS
import binascii

class Patch:
    def __init__(self, rom, states={}):
        self.base_rom = rom
        self.game = self.base_rom.game
        self.ips_patch = PatchIPS.load(self.game.patch)
        self.rom = None

        # dictionary of states, key is index, value is state namedtuple
        self.states = states

    def extract_all_states(self, rom_file_path):
        with open(rom_file_path, 'rb') as f:
            rom = f.read()
        num_states = (len(rom) - self.game.base * 16384) // 32768
        index = 0
        for i in range(num_states):
            state = self.extract_state(rom, i)
            if(len(array_trim(state.wram)) != 0):
                self.states[index] = state
                index += 1

    def extract_state(self, rom, index):
        base = self.game.base
        home = self.game.home
        bank1 = base + index * 2
        bank2 = bank1 + 1

        vram = rom[to_full(bank1, 20480):to_full(bank1, 20480) + 8192]
        hram = rom[to_full(bank1, 30720):to_full(bank1, 30720) + 256]
        sram1 = rom[to_full(bank1, 31336):to_full(bank1, 31336) + 1432]
        sram2 = rom[to_full(bank2, 20596):to_full(bank2, 20596) + 3980]
        wram = rom[to_full(bank2, 24576):to_full(bank2, 24576) + 8192]
        palette = bytearray(2048)
        bgp = bytearray(64)
        objp = bytearray(64)
        if self.game.cgb:
            palette = rom[to_full(bank1, 28672):to_full(bank1, 28672) + 2048]
            bgp = rom[to_full(bank1, 30976):to_full(bank1, 30976) + 64]
            objp = rom[to_full(bank1, 30140):to_full(bank1, 30140) + 64]
        tail = rom[to_full(bank2, 0x40bc):to_full(bank2, 0x40bc) + 54]
        name = rom[to_full(home, 28672) + index * 18:to_full(home, 28672) + index * 18 + 18]

        return State(self.game.cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail)

    # states = dictionary, key = index, value = state obj
    def inject_all_states(self):
        self.rom = self.ips_patch.apply(self.base_rom.contents)
        self.rom = pad_array(self.rom, self.game.base + len(self.states) * 2)

        for i in range(len(self.states)):
            self.inject_state(self.rom, self.states[i], i)

        self.write_checksum(self.rom)

    def inject_state(self, rom, state, index):
        base = self.game.base
        home = self.game.home
        bank1 = base + index * 2
        bank2 = bank1 + 1

        array_copy(rom, to_full(home, 16384), rom, to_full(bank1, 16384), 4096)
        array_copy(rom, to_full(home, 16384), rom, to_full(bank2, 16384), 4096)
        array_copy(state.vram, 0, rom, to_full(bank1, 20480))
        array_copy(state.hram, 0, rom, to_full(bank1, 30720))
        array_copy(state.sram1, 0, rom, to_full(bank1, 31336))
        array_copy(state.sram2, 0, rom, to_full(bank2, 20596))
        array_copy(state.wram, 0, rom, to_full(bank2, 24576))
        if self.game.cgb:
            array_copy(state.palette, 0, rom, to_full(bank1, 28672))
            array_copy(state.bgp, 0, rom, to_full(bank1, 30976))
            array_copy(state.objp, 0, rom, to_full(bank1, 31040))

        array_copy(state.tail, 0, rom, to_full(bank2, 0x40bc))
        array_copy(state.name, 0, rom, to_full(home, 28672) + index * 18)

        rom[to_full(bank1, 0x408b)] = bank2 & 0xFF

    def write_checksum(self, rom):
        header = -1 * sum(rom[308:333]) - (333-308)
        rom[333] = header & 0xFF

        glob = sum([x & 0xFF for idx, x in enumerate(rom) if idx != 334 and idx != 335])

        rom[334] = glob >> 8 & 0xFF
        rom[335] = glob & 0xFF


class State:
    def __init__(self, cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail):
        self.cgb = cgb
        self.name = name
        self.vram = vram
        self.hram = hram
        self.sram1 = sram1
        self.sram2 = sram2
        self.wram = wram
        self.palette = palette
        self.bgp = bgp
        self.objp = objp
        self.tail = tail

    def set_name(self, name):
        self.name = encode_name(name.strip())

    def get_name(self):
        return decode_name(self.name).strip()


# state is bytearray of savestate
def get_state_offsets(state):
    save_state_labels = dict()
    offset = 3
    size = read_int_be(state[offset:offset+3])
    offset += size + 3

    while offset < len(state):
        key_size = state.index(0, offset) - offset
        key = bytearray(key_size)
        array_copy(state, offset, key, 0, key_size)
        offset += key_size + 1
        size = read_int_be(state[offset:offset+3])
        offset += 3
        key_string = "".join([chr(c) for c in key])
        save_state_labels[key_string] = (offset, size)
        offset += size

    return save_state_labels


# state is bytearray of savestate
def extract_state_data(state, labels):
    state_offsets = get_state_offsets(state)
    hashes = dict()

    for key in labels:
        index = state_offsets[key][0]
        size = state_offsets[key][1]
        hashes[key] = bytearray(state[index:index+size])

    return hashes


def delay_cycles(cycles):
    opcodes = bytearray()
    if cycles >= 36:
        loops = (cycles - 8) // 28
        cycles -= 8 + loops  * 28
        opcodes.extend([1, loops & 0xFF, loops >> 8, 11, 121, 176, 32, 251])

    if cycles >= 4:
        for i in range(cycles // 4):
            opcodes.append(0)

    return opcodes


def pad_array(source, max):
    size = 1
    while(2 << size < max):
        size += 1

    result = bytearray(32768 << size)
    array_copy(source, 0, result, 0)
    result[328] = size & 0xFF
    return result


def to_full(a, b):
    return a * 16384 + b - 16384


def make_state(state_name, gsr_state, cgb):
    with open(gsr_state, 'rb') as f:
        gsrState = f.read()
    data = extract_state_data(gsrState, ['vram', 'sram', 'wram', 'hram', 'pc', 'sp', 'a', 'b', 'c', 'd', 'e', 'f', 'h', 'l', 'vcycles', 'cc', 'ldivup', 'bgp', 'objp'])

    if read_int_be(data['pc']) != 64:
        print('!')

    sp = read_int_be(data['sp'])
    ret = read_int_le(data['wram'][sp-49152:sp-49152 + 2])
    vcycles = read_int_be(data['vcycles'])
    cc = read_int_be(data['cc'])
    ldivup = read_int_be(data['ldivup'])

    div = cc & 0xFFFF

    #backwards compat
    if data['hram'][260]:
        div = data['hram'][260] * 256 + cc - ldivup

    data['hram'][320] = data['hram'][320] & 0x7F
    data['hram'][341] = 0

    vram = data['vram'][:8192]
    hram = data['hram'][256:512]
    sram1 = data['sram'][:1432]
    sram2 = data['sram'][9624:9624+3980]
    wram = data['wram'][:8192]
    palette = bytearray(2048)
    bgp = bytearray(64)
    objp = bytearray(64)

    if cgb:
        palette = data['vram'][14336:14336+2048]
        bgp = data['bgp'][:64]
        objp = data['objp'][:64]

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
    regs.extend(data['f'])
    regs.extend(data['a'])
    regs.extend([197, 241, 1])
    regs.extend(data['c'])
    regs.extend(data['b'])
    regs.append(17)
    regs.extend(data['e'])
    regs.extend(data['d'])
    regs.append(33)
    regs.extend(data['l'])
    regs.extend(data['h'])
    regs.append(251)
    regs.append(195)
    regs.extend([ret & 0xFF, (ret >> 8) & 0xFF])

    tail = bytearray(lcd + delay1 + rdiv + delay2 + regs)
    name = encode_name(state_name)

    return State(cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail)


def read_int_be(b):
    return int.from_bytes(b, 'big')


def read_int_le(b):
    return int.from_bytes(b, 'little')


def encode_name(name):
    encoded_name = bytearray()
    for i in name:
        poke_char = 0
        if i == ' ':
            poke_char = 127
        elif i >= '0' and i <= '9':
            poke_char = 246 + ord(i) - 48
        elif i >= 'A' and i <= 'Z':
            poke_char = 128 + ord(i) - 65
        elif i >= 'a' and i <= 'z':
            poke_char = 160 + ord(i) - 97

        encoded_name.append(poke_char)

    if len(encoded_name) > 16:
        encoded_name.append(117)

    return encoded_name


def decode_name(name):
    decoded_name = ''
    for i in name:
        poke_char = i & 0xFF
        c = ''
        if poke_char == 127:
            c = ' '
        elif poke_char >= 246 and poke_char <= 255:
            c = chr(48 + poke_char - 246)
        elif poke_char >= 128 and poke_char <= 153:
            c = chr(65 + poke_char - 128)
        elif poke_char >= 160 and poke_char <= 185:
            c = chr(97 + poke_char - 160)
        decoded_name += c

    return decoded_name
