# converts a NULL-terminated binary string to an ordinary string.
def decode(bs: bytes) -> str:
    end = bs.find(b"\0")  # find null termination
    if end == -1:  # if none exists, there is no end.
        return bs.decode()
    return bs[:end].decode()  # otherwise cut it off at end