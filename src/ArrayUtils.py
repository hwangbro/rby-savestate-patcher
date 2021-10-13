# Note: Illegal Windows chars in filenames: <>:"/\|?*
special_chars = {
    " ": 0x7F,
    "(": 0x9A,
    ")": 0x9B,
    ":": 0x9C,
    ";": 0x9D,
    "[": 0x9E,
    "]": 0x9F,
    "é": 0xBA,
    "'": 0xE0,
    "-": 0xE3,
    "?": 0xE6,
    "!": 0xE7,
    ".": 0xF2,
    ",": 0xF4,
}
special_chars_inv = {special_chars[k] : k for k in special_chars}

def array_copy(source, srcOffset, destination, destOffset, size=None):
    if size is None:
        size = len(source)
    destination[destOffset:destOffset+size] = source[srcOffset:srcOffset+size]

def array_trim(source):
    i = len(source) - 1
    while(i >= 0 and source[i] == 0):
        i -= 1

    ret = bytearray(i+1)
    array_copy(source, 0, ret, 0, i+1)
    return ret

def encode_name(name: str) -> bytearray:
    encoded_name = bytearray()
    for i in name:
        poke_char = special_chars['?']
        if i >= '0' and i <= '9':
            poke_char = 246 + ord(i) - 48
        elif i >= 'A' and i <= 'Z':
            poke_char = 128 + ord(i) - 65
        elif i >= 'a' and i <= 'z':
            poke_char = 160 + ord(i) - 97
        elif i in special_chars:
            poke_char = special_chars[i]

        encoded_name.append(poke_char)

        if len(encoded_name) == 18:
            encoded_name[16] = 0x75 # ellipsis
            encoded_name[17] = 0x50 # string terminator
            break

    return encoded_name

def decode_name(name: bytearray) -> str:
    decoded_name = ''
    for i in name:
        poke_char = i & 0xFF
        c = ''
        if poke_char >= 246 and poke_char <= 255:
            c = chr(48 + poke_char - 246)
        elif poke_char >= 128 and poke_char <= 153:
            c = chr(65 + poke_char - 128)
        elif poke_char >= 160 and poke_char <= 185:
            c = chr(97 + poke_char - 160)
        elif poke_char in special_chars_inv:
            c = special_chars_inv[poke_char]
        decoded_name += c

    return decoded_name

def delay_cycles(cycles: int) -> bytearray:
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

def to_full(a: int, b: int) -> int:
    return a * 16384 + b - 16384

def read_int_be(b: bytearray) -> int:
    return int.from_bytes(b, 'big')

def read_int_le(b: bytearray) -> int:
    return int.from_bytes(b, 'little')
