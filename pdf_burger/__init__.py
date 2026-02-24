"""pdf-burger: Merge multiple PDF files into one."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdf-burger")
except PackageNotFoundError:
    __version__ = "unknown"
