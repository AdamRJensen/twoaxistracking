try:  # pragma: no cover
    from importlib.metadata import PackageNotFoundError, version
except ImportError:  # pragma: no cover
    # for python < 3.8 (remove when dropping 3.7 support)
    from importlib_metadata import PackageNotFoundError, version

try:  # pragma: no cover
    __version__ = version(__package__)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0+unknown"


# Import of functions that should be accessible from the package top-level
from .layout import generate_field_layout  # noqa: F401
from .shading import shaded_fraction  # noqa: F401
from .trackerfield import TrackerField  # noqa: F401
