#encoding: utf8

import rejit.loadcode as loadcode

def test_dynamic_code_loading():
    # mov eax, dword ptr 7
    # ret
    binary = b'\xb8\x07\x00\x00\x00\xc3'
    code = loadcode.load(binary)
    assert(loadcode.call(code, "elo", 3) == 7)

