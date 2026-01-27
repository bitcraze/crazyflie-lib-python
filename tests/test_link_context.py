"""Tests for LinkContext scanning functionality."""

import pytest

from cflib._rust import LinkContext


class TestLinkContextValidation:
    """Test address validation in LinkContext.scan()"""

    @pytest.mark.asyncio
    async def test_scan_address_too_short(self) -> None:
        """Scan should reject addresses shorter than 5 bytes"""
        context = LinkContext()
        short_address = [0xE7, 0xE7, 0xE7, 0xE7]  # Only 4 bytes

        with pytest.raises(Exception) as exc_info:
            await context.scan(address=short_address)

        assert "Address must be exactly 5 bytes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scan_address_too_long(self) -> None:
        """Scan should reject addresses longer than 5 bytes"""
        context = LinkContext()
        long_address = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7, 0xE7]  # 6 bytes

        with pytest.raises(Exception) as exc_info:
            await context.scan(address=long_address)

        assert "Address must be exactly 5 bytes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scan_address_exact_length_validates(self) -> None:
        """Scan should accept addresses of exactly 5 bytes (validation passes)"""
        context = LinkContext()
        valid_address = [0xE7, 0xE7, 0xE7, 0xE7, 0xE7]  # Exactly 5 bytes

        # This will fail to scan (no hardware), but validation should pass
        # We're only testing that the address length validation succeeds
        try:
            await context.scan(address=valid_address)
        except Exception as e:
            # If it errors, it should NOT be a validation error
            assert "Address must be exactly 5 bytes" not in str(e)
            # It's fine if it fails for other reasons (no hardware, no radio, etc.)

    @pytest.mark.asyncio
    async def test_scan_default_address(self) -> None:
        """Scan with no address should use default (no validation error)"""
        context = LinkContext()

        # This will fail to scan (no hardware), but should not raise validation error
        try:
            await context.scan()  # No address = use default
        except Exception as e:
            # Should NOT be a validation error
            assert "Address must be exactly 5 bytes" not in str(e)
