# Copyright (C) 2021-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import os
import shutil
from subprocess import PIPE, run
from typing import Any, Dict, Iterator, Optional

from swh.lister.pattern import StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

from ..pattern import CredentialsType

logger = logging.getLogger(__name__)

PageType = str


def opam() -> str:
    """Get the path to the opam executable.

    Raises:
      EnvironmentError if no opam executable is found
    """
    ret = shutil.which("opam")
    if not ret:
        raise EnvironmentError("No opam executable found in path {os.environ['PATH']}")

    return ret


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
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
        opam_root: str = "/tmp/opam/",
    ):
        super().__init__(
            scheduler=scheduler,
            credentials=credentials,
            url=url,
            instance=instance,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )
        self.env = os.environ.copy()
        # Opam root folder is initialized in the :meth:`get_pages` method as no
        # side-effect should happen in the constructor to ease instantiation
        self.opam_root = opam_root

    def get_pages(self) -> Iterator[PageType]:
        # Initialize the opam root directory
        opam_init(self.opam_root, self.instance, self.url, self.env)

        # Actually list opam instance data
        proc = run(
            [
                opam(),
                "list",
                "--all",
                "--no-switch",
                "--safe",
                "--repos",
                self.instance,
                "--root",
                self.opam_root,
                "--normalise",
                "--short",
            ],
            env=self.env,
            stdout=PIPE,
            text=True,
            check=True,
        )

        if proc.stdout is not None:
            yield from proc.stdout.splitlines()

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
                "opam_root": self.opam_root,
                "opam_instance": self.instance,
                "opam_url": self.url,
                "opam_package": page,
            },
        )


def opam_init(opam_root: str, instance: str, url: str, env: Dict[str, Any]) -> None:
    """Initialize an opam_root folder.

    Args:
        opam_root: The opam root folder to initialize
        instance: Name of the opam repository to add or initialize
        url: The associated url of the opam repository to add or initialize
        env: The global environment to use for the opam command.

    Returns:
        None.

    """
    if not os.path.exists(opam_root) or not os.listdir(opam_root):
        command = [
            opam(),
            "init",
            "--reinit",
            "--bare",
            "--no-setup",
            "--root",
            opam_root,
            instance,
            url,
        ]
    else:
        # The repository exists and is populated, we just add another instance in the
        # repository. If it's already setup, it's a noop
        command = [
            opam(),
            "repository",
            "add",
            "--set-default",
            "--root",
            opam_root,
            instance,
            url,
        ]
    # Actually execute the command
    run(command, env=env, check=True)
