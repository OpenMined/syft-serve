"""Basic tests for syft-serve"""


def test_import():
    """Test that syft_serve can be imported"""
    import syft_serve

    assert syft_serve.__version__


def test_version():
    """Test version string"""
    import syft_serve

    assert isinstance(syft_serve.__version__, str)
    assert "." in syft_serve.__version__