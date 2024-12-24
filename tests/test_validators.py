import pytest
from lazyfeed.widgets.validators import is_valid_url


@pytest.mark.parametrize(
    "url, expected",
    [
        ("", False),
        ("://example.com", False),
        ("ftp://example.com", True),
        ("htp://example.com", False),
        ("http//example.com", False),
        ("http://", False),
        ("http://-example.com", False),
        ("http://.com", False),
        ("http://123.123.123.123:80/resource", True),
        ("http://192.168.1.1", True),
        ("http://example-.com", False),
        ("http://example..com", False),
        ("http://example.co.uk", True),
        ("http://example.com", True),
        ("http://example.com#fragment", False),
        ("http://example.com:8080", True),
        ("http://example.com:abc", False),
        ("http://example.com?query=param", True),
        ("http://localhost", True),
        ("http:/example.com", False),
        ("https://example.com", True),
        ("https://example.com/path/to/resource", True),
        ("https://subdomain.example.com", True),
    ],
)
def test_is_valid_url(url, expected):
    assert is_valid_url(url) == expected
