# Copyright (C) 2023 The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from json import loads
import logging
from typing import Iterator, Optional

from swh.lister.pattern import CredentialsType, StatelessLister
from swh.scheduler.interface import SchedulerInterface
from swh.scheduler.model import ListedOrigin

logger = logging.getLogger(__name__)

Origin = str


class GitilesLister(StatelessLister[Origin]):
    """Lister class for Gitiles repositories.

    This lister will retrieve the list of published git repositories by
    parsing the json page found at the url `<url>?format=json`.

    """

    LISTER_NAME = "gitiles"

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        credentials: Optional[CredentialsType] = None,
        max_origins_per_page: Optional[int] = None,
        max_pages: Optional[int] = None,
        enable_origins: bool = True,
    ):
        """Lister class for Gitiles repositories.

        Args:
            url: (Optional) Root URL of the Gitiles instance, i.e. url of the index of
                published git repositories on this instance. Defaults to
                :file:`https://{instance}` if unset.
            instance: Name of gitiles instance. Defaults to url's network location
                if unset.

        """
        super().__init__(
            scheduler=scheduler,
            url=url,
            instance=instance,
            credentials=credentials,
            max_origins_per_page=max_origins_per_page,
            max_pages=max_pages,
            enable_origins=enable_origins,
        )

        self.session.headers.update({"Accept": "application/json"})

    def get_pages(self) -> Iterator[Origin]:
        """Generate git 'project' URLs found on the current Gitiles server."""
        response = self.http_request(f"{self.url}?format=json")
        text = response.text
        # current gitiles' json is returned with a specific prefix
        # See. https://github.com/google/gitiles/issues/263
        if text.startswith(")]}'\n"):
            text = text[5:]

        data = loads(text)

        for repo in data.values():
            yield repo["clone_url"]

    def get_origins_from_page(self, origin: Origin) -> Iterator[ListedOrigin]:
        """Convert a page of gitiles repositories into a list of ListedOrigins."""
        assert self.lister_obj.id is not None

        yield ListedOrigin(
            lister_id=self.lister_obj.id,
            url=origin,
            visit_type="git",
        )
