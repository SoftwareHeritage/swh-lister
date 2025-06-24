# Copyright (C) 2018-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from importlib.metadata import PackageNotFoundError, entry_points, version
import logging

logger = logging.getLogger(__name__)


try:
    __version__ = version("swh-lister")
except PackageNotFoundError:
    __version__ = "devel"

USER_AGENT_TEMPLATE = (
    f"Software Heritage %s lister v{__version__}"
    " (+https://www.softwareheritage.org/contact)"
)

LISTERS = {
    entry_point.name.split(".", 1)[1]: entry_point
    for entry_point in entry_points().select(group="swh.workers")
    if entry_point.name.split(".", 1)[0] == "lister"
}


SUPPORTED_LISTERS = list(LISTERS)

TARBALL_EXTENSIONS = [
    ".crate",
    ".gem",
    ".jar",
    ".love",  # zip
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tbz",
    ".tbz2",
    ".bz2",
    ".bzip2",
    ".tar.lzma",
    ".tar.lz",
    ".txz",
    ".tar.xz",
    ".tar.z",
    ".tar.Z",
    ".7z",
    ".oxt",  # zip
    ".pak",  # zip
    ".war",  # zip
    ".whl",  # zip
    ".vsix",  # zip
    ".VSIXPackage",  # zip
    ".tar.zst",
]
"""Tarball recognition pattern"""


def get_lister(lister_name, db_url=None, **conf):
    """Instantiate a lister given its name.

    Args:
        lister_name (str): Lister's name
        conf (dict): Configuration dict (lister db cnx, policy, priority...)

    Returns:
        Tuple (instantiated lister, drop_tables function, init schema function,
        insert minimum data function)

    """
    if lister_name not in LISTERS:
        raise ValueError(
            "Invalid lister %s: only supported listers are %s"
            % (lister_name, SUPPORTED_LISTERS)
        )
    if db_url:
        conf["lister"] = {"cls": "postgresql", "db": db_url}

    registry_entry = LISTERS[lister_name].load()()
    lister_cls = registry_entry["lister"]

    from swh.lister import pattern

    if issubclass(lister_cls, pattern.Lister):
        return lister_cls.from_config(**conf)
    else:
        # Old-style lister
        return lister_cls(override_config=conf)
