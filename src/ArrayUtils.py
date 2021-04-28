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
