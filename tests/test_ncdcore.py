from saxs_bluesky.utils.ncdcore import NCDCore


def test_decimal_to_binary():
    assert NCDCore.decimal_to_binary(192) == "11000000"


def test_binary_to_decimal():
    assert NCDCore.binary_to_decimal("11000000") == 192


def test_str2bool():
    assert NCDCore.str2bool("y")
    assert not NCDCore.str2bool("N")


def test_to_seconds():
    assert NCDCore.to_seconds("MS") == 1e-3
