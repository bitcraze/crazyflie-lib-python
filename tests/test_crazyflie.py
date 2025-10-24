import pytest


class TestCrazyflieConnection:
    """Test Crazyflie connection functionality"""

    def test_crazyflie_invalid_uri_raises_exception(self) -> None:
        """Crazyflie.connect_from_uri() should raise exception for invalid URI"""
        from cflib._rust import Crazyflie

        # Attempting to connect to invalid URI should fail
        with pytest.raises(Exception):
            Crazyflie.connect_from_uri("invalid://bad/uri")
