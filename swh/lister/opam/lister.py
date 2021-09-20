# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io
import logging
import os
from subprocess import PIPE, Popen, call
import tempfile
from typing import Iterator, Optional

from swh.lister.pattern import StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType

logger = logging.getLogger(__name__)

PageType = str


class OpamLister(StatelessLister[PageType]):
    """
    List all repositories hosted on an opam repository.

    On initialisation, we create an opam root, with no ocaml compiler (no switch)
    as we won't need it and it's costly. In this opam root, we add a single opam
    repository (url) and give it a name (instance). Then, to get pages, we just ask
    opam to list all the packages for our opam repository in our opam root.

    Args:
        url: base URL of an opam repository
            (for instance https://opam.ocaml.org)
        instance: string identifier for the listed repository

    """

    # Part of the lister API, that identifies this lister
    LISTER_NAME = "opam"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: Optional[str] = None,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler, credentials=credentials, url=url, instance=instance,
        )
        self.env = os.environ.copy()
        # Opam root folder is initialized in the :meth:`get_pages` method as no
        # side-effect should happen in the constructor to ease instantiation
        self.opamroot = tempfile.mkdtemp(prefix="swh_opam_lister")

    def get_pages(self) -> Iterator[PageType]:
        # Initialize the opam root directory with the opam instance data to list.
        call(
            [
                "opam",
                "init",
                "--reinit",
                "--bare",
                "--no-setup",
                "--root",
                self.opamroot,
                self.instance,
                self.url,
            ],
            env=self.env,
        )
        # Actually list opam instance data
        proc = Popen(
            [
                "opam",
                "list",
                "--all",
                "--no-switch",
                "--repos",
                self.instance,
                "--root",
                self.opamroot,
                "--normalise",
                "--short",
            ],
            env=self.env,
            stdout=PIPE,
        )
        if proc.stdout is not None:
            for line in io.TextIOWrapper(proc.stdout):
                yield line.rstrip("\n")

    def get_origins_from_page(self, page: PageType) -> Iterator[ListedOrigin]:
        """Convert a page of OpamLister repositories into a list of ListedOrigins"""
        assert self.lister_obj.id is not None
        # a page is just a package name
        url = f"opam+{self.url}/packages/{page}/"
        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            visit_type="opam",
            url=url,
            last_update=None,
            extra_loader_arguments={
                "opam_root": self.opamroot,
                "opam_instance": self.instance,
                "opam_url": self.url,
                "opam_package": page,
            },
        )
