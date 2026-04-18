"""Shared helpers for in-memory upload objects used in tests."""

from io import BytesIO


class InMemoryUpload(BytesIO):
    """BytesIO variant that mimics Django uploaded file metadata."""

    name: str

    def __init__(self, initial_bytes: bytes | None = None, name: str = "upload.bin"):
        super().__init__(initial_bytes or b"")
        self.name = name

    @property
    def size(self) -> int:
        return self.getbuffer().nbytes
