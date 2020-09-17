# Copyright (C) 2015-2018 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import abc
import logging

from .lister_base import ListerBase
from .lister_transports import ListerHttpTransport


class PageByPageLister(ListerBase):
    """Lister* intermediate class for any service that follows the simple
       pagination page pattern.

    - Client sends a request to list repositories starting from a
      given page identifier.

    - Client receives structured (json/xml/etc) response with
      information about a sequential series of repositories (per page)
      starting from a given index. And, if available, some indication
      of the next page index for fetching the remaining repository
      data.

    See :class:`swh.lister.core.lister_base.ListerBase` for more
    details.

    This class cannot be instantiated. To create a new Lister for a
    source code listing service that follows the model described
    above, you must subclass this class. Then provide the required
    overrides in addition to any unmet implementation/override
    requirements of this class's base (see parent class and member
    docstrings for details).

    Required Overrides::

        def get_next_target_from_response

    """

    @abc.abstractmethod
    def get_next_target_from_response(self, response):
        """Find the next server endpoint page given the entire response.

        Implementation of this method depends on the server API spec
        and the shape of the network response object returned by the
        transport_request method.

        For example, some api can use the headers links to provide the
        next page.

        Args:
            response (transport response): response page from the server

        Returns:
            index of next page, possibly extracted from a next href url

        """
        pass

    @abc.abstractmethod
    def get_pages_information(self):
        """Find the total number of pages.

        Implementation of this method depends on the server API spec
        and the shape of the network response object returned by the
        transport_request method.

        For example, some api can use dedicated headers:
        - x-total-pages to provide the total number of pages
        - x-total to provide the total number of repositories
        - x-per-page to provide the number of elements per page

        Returns:
            tuple (total number of repositories, total number of
            pages, per_page)

        """
        pass

    # You probably don't need to override anything below this line.

    def do_additional_checks(self, models_list):
        """Potentially check for existence of repositories in models_list.

        This will be called only if check_existence is flipped on in
        the run method below.

        """
        for m in models_list:
            sql_repo = self.db_query_equal("uid", m["uid"])
            if sql_repo:
                return False
        return models_list

    def run(self, min_bound=None, max_bound=None, check_existence=False):
        """Main entry function. Sequentially fetches repository data from the
           service according to the basic outline in the class
           docstring. Continually fetching sublists until either there
           is no next page reference given or the given next page is
           greater than the desired max_page.

        Args:
            min_bound: optional page to start from
            max_bound: optional page to stop at
            check_existence (bool): optional existence check (for
                                    incremental lister whose sort
                                    order is inverted)

        Returns:
            nothing

        """
        status = "uneventful"
        page = min_bound or 0
        loop_count = 0

        self.min_page = min_bound
        self.max_page = max_bound

        while self.is_within_bounds(page, self.min_page, self.max_page):
            logging.info("listing repos starting at %s" % page)

            response, injected_repos = self.ingest_data(page, checks=check_existence)
            if not response and not injected_repos:
                logging.info("No response from api server, stopping")
                break
            elif not injected_repos:
                logging.info("Repositories already seen, stopping")
                break
            status = "eventful"

            next_page = self.get_next_target_from_response(response)

            # termination condition

            if (next_page is None) or (next_page == page):
                logging.info("stopping after page %s, no next link found" % page)
                break
            else:
                page = next_page

            loop_count += 1
            if loop_count == 20:
                logging.info("flushing updates")
                loop_count = 0
                self.db_session.commit()
                self.db_session = self.mk_session()

        self.db_session.commit()
        self.db_session = self.mk_session()

        return {"status": status}


class PageByPageHttpLister(ListerHttpTransport, PageByPageLister):
    """Convenience class for ensuring right lookup and init order when
       combining PageByPageLister and ListerHttpTransport.

    """

    def __init__(self, url=None, override_config=None):
        PageByPageLister.__init__(self, override_config=override_config)
        ListerHttpTransport.__init__(self, url=url)
