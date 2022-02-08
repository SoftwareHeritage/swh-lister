.. _lister-tutorial:

Tutorial: list the content of your favorite forge in just a few steps
=====================================================================

Overview
--------

The three major phases of work in Software Heritage's preservation process, on the
technical side, are *listing software sources*, *scheduling updates* and *loading the
software artifacts into the archive*.

A previous effort in 2017 consisted in designing the framework to make lister a
straightforward "fill in the blanks" process, based on gained experience on the
diversity found in the listed services. This is the second iteration on the lister
framework design, comprising a library and an API which is easier to work with and less
"magic" (read implicit). This new design is part of a larger effort in redesigning the
scheduling system for the recurring tasks updating the content of the archive.

.. _fundamentals:

Fundamentals
------------

Fundamentally, a basic lister must follow these steps:

1. Issue a network request for a service endpoint.
2. Convert the response data into a model object.
3. Send the model object to the scheduler.

Steps 1 and 3 are generic problems, that are often already solved by helpers or in other
listers. That leaves us mainly to implement step 2, which is simple when the remote
service provides an API.

.. _prerequisites:

Prerequisites
-------------

Skills:

* object-oriented Python
* requesting remote services through HTTP
* scrapping if no API is offered

Analysis of the target service. Prepare the following elements to write the lister:

* instance names and URLs
* requesting scheme: base URL, path, query_string, POST data, headers
* authentication types and which one to support, if any
* rate-limiting: HTTP codes and headers used
* data format: JSON/XML/HTML/...?
* mapping between remote data and needed data (ListedOrigin model, internal state)

We will now walk through the steps to build a new lister.
Please use this template to start with: :download:`new_lister_template.py`

.. _lister-declaration:

Lister declaration
------------------

In order to write a lister, two basic elements are required. These are the
:py:class:`Lister` base class and the :py:class:`ListedOrigin` scheduler model class.
Optionally, for listers that need to keep a state and support incremental listing, an
additional object :py:class:`ListerState` will come into play.

Each lister must subclass :py:class:`Lister <swh.lister.pattern.Lister>` either directly
or through a subclass such as :py:class:`StatelessLister
<swh.lister.pattern.StatelessLister>` for stateless ones.

We extensively type-annotate our listers, as any new code, which makes proeminent that
those lister classes are generic, and take the following parameters:

* :py:class:`Lister`: the lister state type, the page type
* :py:class:`StatelessLister`: only the page type

You can can start by declaring a stateless lister and leave the implementation of state
for later if the listing needs it. We will see how to in :ref:`handling-lister-state`.

Both the lister state type and the page type are user-defined types. However, while the
page type may only exist as a type annotation, the state type for a stateful lister must
be associated with a concrete object. The state type is commonly defined as a dataclass
whereas the page type is often a mere annotation, potentially given a nice alias.

Example lister declaration::

    NewForgePage = List[Dict[str, Any]]

    @dataclass
    class NewForgeListerState:
        ...

    class NewForgeLister(Lister[NewForgeListerState, NewForgePage]):
        LISTER_NAME = "My"
        ...

The new lister must declare a name through the :py:attr:`LISTER_NAME` class attribute.

.. _lister-construction:

Lister construction
-------------------

The lister constructor is only required to ask for a :py:class:`SchedulerInterface`
object to pass to the base class. But it does not mean that it is all that's needed for
it to useful. A lister need information on which remote service to talk to. It needs an
URL.

Some services are centralized and offered by a single organization. Think of Github.
Others are offered by many people across the Internet, each using a different hosting,
each providing specific data. Think of the many Gitlab instances. We need a name to
identify each instance, and even if there is only one, we need its URL to access it
concretely.

Now, you may think of any strategy to infer the information or hardcode it, but the base
class needs an URL and an instance name. In any case, for a multi-instance service, you
better be explicit and require the URL as constructor argument. We recommend the URL to
be some form of a base URL, to be concatenated with any variable part appearing either
because there exist multiple instances or the URL need recomputation in the listing
process.

If we need any credentials to access a remote service, and do so in our polite but
persistent fashion (remember that we want fresh information), you are encouraged to
provide support for authenticated access. The base class support handling credentials as
a set of identifier/secret pair. It knows how to load from a secrets store the right
ones for the current ("lister name", "instance name") setting, if none were originally
provided through the task parameters. You can ask for other types of access tokens in a
separate parameter, but then you lose this advantage.

Example of a typical lister constructor::

    def __init__(
        self,
        scheduler: SchedulerInterface,
        url: str,
        instance: str,
        credentials: CredentialsType = None,
    ):
        super().__init__(
            scheduler=scheduler, url=url, instance=instance, credentials=credentials,
        )
        ...

.. _core-lister-functionality:

Core lister functionality
-------------------------

For the lister to contribute data to the archive, you now have to write the logic to
fetch data from the remote service, and format it in the canonical form the scheduler
expects, as outined in :ref:`fundamentals`. To this purpose, the two methods to
implement are::

    def get_pages(self) -> Iterator[NewForgePage]:
        ...

    def get_origins_from_page(self, page: NewForgePage) -> Iterator[ListedOrigin]:
        ...

Those two core functions are called by the principal lister method,
:py:meth:`Lister.run`, found in the base class.

:py:meth:`get_pages` is the guts of the lister. It takes no arguments and must produce
data pages. An iterator is fine here, as the :py:meth:`Lister.run` method only mean to
iterate in a single pass on it. This method gets its input from a network request to a
remote service's endpoint to retrieve the data we long for.

Depending on whether the data is adequately structured for our purpose can be tricky.
Here you may have to show off your data scraping skills, or just consume a well-designed
API. Those aspects are discussed more specifically in the section
:ref:`handling-specific-topics`.

In any case, we want the data we return to be usefully filtered and structured. The
easiest way to create an iterator is to use the ``yield`` keyword. Yield each data page
you have structured in accordance with the page type you have declared. The page type
exists only for static type checking of data passed from :py:meth:`get_pages` to
:py:meth:`get_origins_from_page`; you can choose whatever fits the bill.

:py:meth:`get_origins_from_page` is simpler. For each individual software origin you
have received in the page, you convert and yield a :py:class:`ListedOrigin` model
object. This datatype has the following mandatory fields:

* lister id: you generally fill this with the value of :py:attr:`self.lister_obj.id`

* visit type: the type of software distribution format the service provides. For use by
  a corresponding loader. It is an identifier, so you have to either use an existing
  value or craft a new one if you get off the beaten track and tackle a new software
  source. But then you will have to discuss the name with the core developers.

  Example: Phabricator is a forge that can handle Git or SVN repositories. The visit
  type would be "git" when listing such a repo that provides a Git URL that we can load.

* origin URL: an URL that, combined with the visit type, will serve as the input of
  loader.

This datatype can also further be detailed with the optional fields:

* last update date: freshness information on this origin, which is useful to the
  scheduler for optimizing its scheduling decisions. Fill it if provided by the service,
  at no substantial additional runtime cost, e.g. in the same request.

* extra loader arguments: extra parameters to be passed to the loader for it to be
  able to load the origin. It is needed for example when additional context is needed
  along with the URL to effectively load from the origin.

See the definition of :swh_web:`ListedOrigin <browse/swh:1:rev:03460207a17d82635ef5a6f12358392143eb9eef/?origin_url=https://forge.softwareheritage.org/source/swh-scheduler.git&path=swh/scheduler/model.py&revision=03460207a17d82635ef5a6f12358392143eb9eef#L134-L177>`.

Now that that we showed how those two methods operate, let's put it together by showing
how they fit in the principal :py:meth:`Lister.run` method::

    def run(self) -> ListerStats:

        full_stats = ListerStats()

        try:
            for page in self.get_pages():
                full_stats.pages += 1
                origins = self.get_origins_from_page(page)
                full_stats.origins += self.send_origins(origins)
                self.commit_page(page)
        finally:
            self.finalize()
            if self.updated:
                self.set_state_in_scheduler()

        return full_stats

:py:meth:`Lister.send_origins` is the method that sends listed origins to the scheduler.

The :py:class:`ListerState` datastructure, defined along the base lister class, is used
to compute the number of listed pages and origins in a single lister run. It is useful
both for the scheduler that automatically collects this information and to test the
lister.

You see that the bulk of a lister run consists in streaming data gathered from the
remote service to the scheduler. And this is done under a ``try...finally`` construct to
have the lister state reliably recorded in case of unhandled error. We will explain the
role of the remaining methods and attributes appearing here in the next section as it is
related to the lister state.

.. _handling-lister-state:

Handling lister state
---------------------

With what we have covered until now you can write a stateless lister. Unfortunately,
some services provide too much data to efficiently deal with it in a one-shot fashion.
Listing a given software source can take several hours or days to process. Our listers
can also give valid output, but fail on an unexpected condition and would have to start
over. As we want to be able to resume the listing process from a given element, provided
by the remote service and guaranteed to be ordered, such as a date or a numeric
identifier, we need to deal with state.

The remaining part of the lister API is reserved for dealing with lister state.

If the service to list has no pagination, then the data set to handle is small enough to
not require keeping lister state. In the opposite case, you will have to determine which
piece of information should be recorded in the lister state. As said earlier, we
recommend declaring a dataclass for the lister state::

    @dataclass
    class NewForgeListerState:
        current: str = ""

    class NewForgeLister(Lister[NewForgeListerState, NewForgePage]):
        ...

A pair of methods, :py:meth:`state_from_dict` and :py:meth:`state_to_dict` are used to
respectively import lister state from the scheduler and export lister state to the
scheduler. Some fields may need help to be serialized to the scheduler, such as dates,
so this needs to be handled there.

Where is the state used? Taking the general case of a paginating service, the lister
state is used at the beginning of the :py:meth:`get_pages` method to initialize the
variables associated with the last listing progress. That way we can start from an
arbitrary element, or just the first one if there is no last lister state.

The :py:meth:`commit_page` is called on successful page processing, after the new
origins are sent to the scheduler. Here you should mainly update the lister state by
taking into account the new page processed, e.g. advance a date or serial field.

Finally, upon either completion or error, the :py:meth:`finalize` is called. There you
must set attribute :py:attr:`updated` to True if you were successful in advancing in the
listing process. To do this you will commonly retrieve the latest saved lister state
from the scheduler and compare with your current lister state. If lister state was
updated, ultimately the current lister state will be recorded in the scheduler.

We have now seen the stateful lister API. Note that some listers may implement more
flexibility in the use of lister state. Some allow an `incremental` parameter that
governs whether or not we will do a stateful listing or not. It is up to you to support
additional functionality if it seems relevant.

.. _handling-specific-topics:

Handling specific topics
------------------------

Here is a quick coverage of common topics left out from lister construction and
:py:meth:`get_pages` descriptions.

Sessions
^^^^^^^^

When requesting a web service repeatedly, most parameters including headers do not
change and could be set up once initially. We recommend setting up a e.g. HTTP session,
as instance attribute so that further requesting code can focus on what really changes.
Some ubiquitous HTTP headers include "Accept" to set to the service response format and
"User-Agent" for which we provide a recommended value :py:const:`USER_AGENT` to be
imported from :py:mod:`swh.lister`. Authentication is also commonly provided through
headers, so you can also set it up in the session.

Transport error handling
^^^^^^^^^^^^^^^^^^^^^^^^

We generally recommend logging every unhandleable error with the response content and
then immediately stop the listing by doing an equivalent of
:py:meth:`Response.raise_for_status` from the ``requests`` library. As for rate-limiting
errors, we have a strategy of using a flexible decorator to handle the retrying for us.
It is based on the ``tenacity`` library and accessible as :py:func:`throttling_retry` from
:py:mod:`swh.lister.utils`.

Pagination
^^^^^^^^^^

This one is a moving target. You have to understand how the pagination mechanics of the
particular service works. Some guidelines though. The identifier may be minimal (an id
to pass as query parameter), compound (a set of such parameters) or complete (a whole
URL). If the service provides the next URL, use it. The piece of information may be
found either in the response body, or in a header. Once identified, you still have to
implement the logic of requesting and extracting it in a loop and quitting the loop when
there is no more data to fetch.

Page results
^^^^^^^^^^^^

First, when retrieving page results, which involves some protocols and parsing logic,
please make sure that any deviance from what was expected will result in an
informational error. You also have to simplify the results, both with filtering request
parameters if the service supports it, and by extracting from the response only the
information needed into a structured page. This all makes for easier debugging.

Misc files
^^^^^^^^^^

There are also a few files that need to be modified outside of the lister directory, namely:

* :file:`/setup.py` to add your lister to the end of the list in the *setup* section::

    entry_points="""
        [swh.cli.subcommands]
        lister=swh.lister.cli
        [swh.workers]
        lister.bitbucket=swh.lister.bitbucket:register
        lister.cgit=swh.lister.cgit:register
        ..."""

* :file:`/swh/lister/tests/test_cli.py` to get a default set of parameters in scheduler-related tests.
* :file:`/README.md` to reference the new lister.
* :file:`/CONTRIBUTORS` to add your name.

Testing your lister
-------------------

When developing a new lister, it's important to test. For this, add the tests
(check :file:`swh/lister/*/tests/`) and register the celery tasks in the main
conftest.py (:file:`swh/lister/core/tests/conftest.py`).

Another important step is to actually run it within the docker-dev
(:ref:`run-lister-tutorial`).

More about listers
------------------

See current implemented listers as examples (GitHub_, Bitbucket_, CGit_, GitLab_ ).

.. _GitHub: https://forge.softwareheritage.org/source/swh-lister/browse/master/swh/lister/github/lister.py
.. _Bitbucket: https://forge.softwareheritage.org/source/swh-lister/browse/master/swh/lister/bitbucket/lister.py
.. _CGit: https://forge.softwareheritage.org/source/swh-lister/browse/master/swh/lister/cgit/lister.py
.. _GitLab: https://forge.softwareheritage.org/source/swh-lister/browse/master/swh/lister/gitlab/lister.py
