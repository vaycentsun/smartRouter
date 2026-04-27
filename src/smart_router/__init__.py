try:
    from importlib.metadata import version
    __version__ = version("smartrouter")
except ImportError:
    __version__ = "1.1.0"