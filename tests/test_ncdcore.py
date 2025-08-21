from saxs_bluesky.utils.ncdcore import ncdcore


def test_decimal_to_binary():
    assert ncdcore.decimal_to_binary(192) == "11000000"


def test_binary_to_decimal():
    assert ncdcore.binary_to_decimal("11000000") == 192


def test_str2bool():
    assert ncdcore.str2bool("y")
    assert not ncdcore.str2bool("N")


def test_to_seconds():
    assert ncdcore.to_seconds("MS") == 1e-3
