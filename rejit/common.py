#encoding: utf8

import string

class RegexError(Exception): pass

supported_chars = string.ascii_letters + string.digits + '`~!@#$%&=_{}:;"\'<>,/'

special_chars = '\\^*()-+[]|?.'

def escape_symbol(symbol):
    return "\\" + symbol if symbol in special_chars else symbol

