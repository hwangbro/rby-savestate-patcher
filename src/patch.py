from ArrayUtils import *
from game import *
from ips_util import Patch as PatchIPS
import binascii

class Patch:
    def __init__(self, rom, states={}):
        self.BaseRom = rom
        self.Game = self.BaseRom.Game
        self.IPSPatch = PatchIPS.load(self.Game.Patch)
        self.rom = None

        # dictionary of states, key is index, value is state namedtuple
        self.States = states

    def extract_all_states(self, romFilePath):
        with open(romFilePath, 'rb') as f:
            rom = f.read()
        numStates = (len(rom) - self.Game.Base * 16384) // 32768
        index = 0
        for i in range(numStates):
            state = self.extract_state(rom, i)
            if(len(array_trim(state.Wram)) != 0):
                self.States[index] = state
                index += 1

    def extract_state(self, rom, index):
        base = self.Game.Base
        home = self.Game.Home
        bank1 = base + index * 2
        bank2 = bank1 + 1

        vram = rom[to_full(bank1, 20480):to_full(bank1, 20480) + 8192]
        hram = rom[to_full(bank1, 30720):to_full(bank1, 30720) + 256]
        sram1 = rom[to_full(bank1, 31336):to_full(bank1, 31336) + 1432]
        sram2 = rom[to_full(bank2, 20596):to_full(bank2, 20596) + 3980]
        wram = rom[to_full(bank2, 24576):to_full(bank2, 24576) + 8192]
        palette = 2048
        bgp = 64
        objp = 64
        if self.Game.Cgb:
            palette = rom[to_full(bank1, 28672):to_full(bank1, 28672) + 2048]
            bgp = rom[to_full(bank1, 30976):to_full(bank1, 30976) + 64]
            objp = rom[to_full(bank1, 30140):to_full(bank1, 30140) + 64]
        tail = rom[to_full(bank2, 16569):to_full(bank2, 16569) + 54]
        name = rom[to_full(home, 28672) + index * 18:to_full(home, 28672) + index * 18 + 18]

        return State(self.Game.Cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail)

    # states = dictionary, key = index, value = state obj
    def inject_all_states(self):
        self.rom = self.IPSPatch.apply(self.BaseRom.Contents)
        self.rom = pad_array(self.rom, self.Game.Base + len(self.States) * 2)

        for i in range(len(self.States)):
            self.inject_state(self.rom, self.States[i], i)

        self.write_checksum(self.rom)

    def inject_state(self, rom, state, index):
        base = self.Game.Base
        home = self.Game.Home
        bank1 = base + index * 2
        bank2 = bank1 + 1

        array_copy(rom, to_full(home, 16384), rom, to_full(bank1, 16384), 4096)
        array_copy(rom, to_full(home, 16384), rom, to_full(bank2, 16384), 4096)
        array_copy(state.Vram, 0, rom, to_full(bank1, 20480))
        array_copy(state.Hram, 0, rom, to_full(bank1, 30720))
        array_copy(state.Sram1, 0, rom, to_full(bank1, 31336))
        array_copy(state.Sram2, 0, rom, to_full(bank2, 20596))
        array_copy(state.Wram, 0, rom, to_full(bank2, 24576))
        if self.Game.Cgb:
            array_copy(state.Palette, 0, rom, to_full(bank1, 28672))
            array_copy(state.Bgp, 0, rom, to_full(bank1, 30976))
            array_copy(state.Objp, 0, rom, to_full(bank1, 31040))

        array_copy(state.Tail, 0, rom, to_full(bank2, 0x40bc))
        array_copy(state.Name, 0, rom, to_full(home, 28672) + index * 18)

        rom[to_full(bank1, 0x408b)] = bank2 & 0xFF

    def write_checksum(self, rom):
        header = -1 * sum(rom[308:333]) - (333-308)
        rom[333] = header & 0xFF

        glob = sum([x & 0xFF for idx, x in enumerate(rom) if idx != 334 and idx != 335])

        rom[334] = glob >> 8 & 0xFF
        rom[335] = glob & 0xFF


class State:
    def __init__(self, cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail):
        self.Cgb = cgb
        self.Name = name
        self.Vram = vram
        self.Hram = hram
        self.Sram1 = sram1
        self.Sram2 = sram2
        self.Wram = wram
        self.Palette = palette
        self.Bgp = bgp
        self.Objp = objp
        self.Tail = tail

    def set_name(self, name):
        self.Name = encode_name(name.strip())

    def get_name(self):
        return decode_name(self.Name).strip()


# state is bytearray of savestate
def get_state_offsets(state):
    saveStateLabels = dict()
    offset = 3
    size = read_int_be(state[offset:offset+3])
    offset += size + 3

    while offset < len(state):
        keySize = state.index(0, offset) - offset
        key = bytearray(keySize)
        array_copy(state, offset, key, 0, keySize)
        offset += keySize + 1
        size = read_int_be(state[offset:offset+3])
        offset += 3
        keyString = "".join([chr(c) for c in key])
        saveStateLabels[keyString] = (offset, size)
        offset += size

    return saveStateLabels


# state is bytearray of savestate
def extract_state_data(state, labels):
    stateOffsets = get_state_offsets(state)
    hashes = dict()

    for key in labels:
        index = stateOffsets[key][0]
        size = stateOffsets[key][1]
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

    # result = bytearray(len(source))
    result = bytearray(32768 << size)
    array_copy(source, 0, result, 0)
    # for i in range(len(result), 32768 << size):
        # result.append(0)

    result[328] = size & 0xFF
    return result


def to_full(a, b):
    return a * 16384 + b - 16384


def make_state(stateName, gsrStateFile, cgb):
    with open(gsrStateFile, 'rb') as f:
        gsrState = f.read()
    data = extract_state_data(gsrState, ['vram', 'sram', 'wram', 'hram', 'pc', 'sp', 'a', 'b', 'c', 'd', 'e', 'f', 'h', 'l', 'vcycles', 'cc', 'ldivup', 'bgp', 'objp'])

    if(read_int_be(data['pc']) != 64):
        print('!')

    sp = read_int_be(data['sp'])
    ret = read_int_le(data['wram'][sp-49152:sp-49152 + 2])
    vcycles = read_int_be(data['vcycles'])
    cc = read_int_be(data['cc'])
    ldivup = read_int_be(data['ldivup'])

    div = cc & 0xFFFF

    #backwards compat
    if(data['hram'][260]):
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
    # tail.extend(lcd)
    # tail.extend(delay1)
    # tail.extend(rdiv)
    # tail.extend(delay2)
    # tail.extend(regs)

    name = encode_name(stateName)

    return State(cgb, name, vram, hram, sram1, sram2, wram, palette, bgp, objp, tail)


def read_int_be(b):
    return int.from_bytes(b, 'big')


def read_int_le(b):
    return int.from_bytes(b, 'little')


def encode_name(name):
    encodedName = bytearray()
    for i in name:
        pokeChar = 0
        if i == ' ':
            pokeChar = 127
        elif i >= '0' and i <= '9':
            pokeChar = 246 + ord(i) - 48
        elif i >= 'A' and i <= 'Z':
            pokeChar = 128 + ord(i) - 65
        elif i >= 'a' and i <= 'z':
            pokeChar = 160 + ord(i) - 97

        encodedName.append(pokeChar)

    if len(encodedName) > 16:
        encodedName.append(117)

    return encodedName


def decode_name(name):
    decodedName = ''
    for i in name:
        pokeChar = i & 0xFF
        c = ''
        if pokeChar == 127:
            c = ' '
        elif pokeChar >= 246 and pokeChar <= 255:
            c = chr(48 + pokeChar - 246)
        elif pokeChar >= 128 and pokeChar <= 153:
            c = chr(65 + pokeChar - 128)
        elif pokeChar >= 160 and pokeChar <= 185:
            c = chr(97 + pokeChar - 160)
        decodedName += c

    return decodedName
