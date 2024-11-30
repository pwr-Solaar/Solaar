from keysyms import keysymdef


def test_keysymdef():
    key_mapping = keysymdef.key_symbols

    assert key_mapping["0"] == 48
    assert key_mapping["A"] == 65
    assert key_mapping["a"] == 97
