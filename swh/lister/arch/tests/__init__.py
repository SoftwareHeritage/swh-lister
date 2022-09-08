# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
from pathlib import PosixPath
import subprocess
from typing import Optional, Union

# TODO: prepare_repository_from_archive method is duplicated from crates lister tests,
# centralize to tests utils?


def prepare_repository_from_archive(
    archive_path: str,
    filename: Optional[str] = None,
    tmp_path: Union[PosixPath, str] = "/tmp",
) -> str:
    """Given an existing archive_path, uncompress it.
    Returns a file repo url which can be used as origin url.

    This does not deal with the case where the archive passed along does not exist.
    """
    if not isinstance(tmp_path, str):
        tmp_path = str(tmp_path)
    # uncompress folder/repositories/dump for the loader to ingest
    subprocess.check_output(["tar", "xf", archive_path, "-C", tmp_path])
    # build the origin url (or some derivative form)
    _fname = filename if filename else os.path.basename(archive_path)
    repo_url = f"file://{tmp_path}/{_fname}"
    return repo_url
