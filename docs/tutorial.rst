.. _lister-tutorial:

Tutorial: list the content of your favorite forge in just a few steps
=====================================================================

(the `original version
<https://www.softwareheritage.org/2017/03/24/list-the-content-of-your-favorite-forge-in-just-a-few-steps/>`_
of this article appeared on the Software Heritage blog)

Back in November 2016, Nicolas Dandrimont wrote about structural code changes
`leading to a massive (+15 million!) upswing in the number of repositories
archived by Software Heritage
<https://www.softwareheritage.org/2016/11/09/listing-47-million-repositories-refactoring-our-github-lister/>`_
through a combination of automatic linkage between the listing and loading
scheduler, new understanding of how to deal with extremely large repository
hosts like `GitHub <https://github.com/>`_, and activating a new set of
repositories that had previously been skipped over.

In the post, Nicolas outlined the three major phases of work in Software
Heritage's preservation process (listing, scheduling updates, loading) and
highlighted that the ability to preserve the world's free software heritage
depends on our ability to find and list the repositories.

At the time, Software Heritage was only able to list projects on
GitHub. Focusing early on GitHub, one of the largest and most active forge in
the world, allowed for a big value-to-effort ratio and a rapid launch for the
archive. As the old Italian proverb goes, "Il meglio è nemico del bene," or in
modern English parlance, "Perfect is the enemy of good," right? Right. So the
plan from the beginning was to implement a lister for GitHub, then maybe
implement another one, and then take a few giant steps backward and squint our
eyes.

Why? Because source code hosting services don't behave according to a unified
standard. Each new service requires dedicated development time to implement a
new scraping client for the non-transferable requirements and intricacies of
that service's API. At the time, doing it in an extensible and adaptable way
required a level of exposure to the myriad differences between these services
that we just didn't think we had yet.

Nicolas' post closed by saying "We haven't carved out a stable API yet that
allows you to just fill in the blanks, as we only have the GitHub lister
currently, and a proven API will emerge organically only once we have some
diversity."

That has since changed. As of March 6, 2017, the Software Heritage **lister
code has been aggressively restructured, abstracted, and commented** to make
creating new listers significantly easier. There may yet be a few kinks to iron
out, but **now making a new lister is practically like filling in the blanks**.

Fundamentally, a basic lister must follow these steps:

1. Issue a network request for a service endpoint.
2. Convert the response into a canonical format.
3. Populate a work queue for fetching and ingesting source repositories.

Steps 1 and 3 are generic problems, so they can get generic solutions hidden
away in the base code, most of which never needs to change. That leaves us to
implement step 2, which can be trivially done now for services with a clean web
APIs.

In the new code, we've tried to hide away as much generic functionality as
possible, turning it into set-and-forget plumbing between a few simple
customized elements. Different hosting services might use different network
protocols, rate-limit messages, or pagination schemes, but, as long as there is
some way to get a list of the hosted repositories, we think that the new base
code will make getting those repositories much easier.

First, let me give you the 30,000 foot view…

The old GitHub-specific lister code looked like this (265 lines of Python):

.. figure:: images/old_github_lister.png

By contrast, the new GitHub-specific code looks like this (34 lines of Python):

.. figure:: images/new_github_lister.png

And the new BitBucket-specific code is even shorter and looks like this (24 lines of Python):

.. figure:: images/new_bitbucket_lister.png

And now this is common shared code in a few abstract base classes, with some new features and loads of docstring comments (in red):

.. figure:: images/new_base.png

So how does the lister code work now, and **how might a contributing developer
go about making a new one**

The first thing to know is that we now have a generic lister base class and ORM
model. A subclass of the lister base should already be able to do almost
everything needed to complete a listing task for a single service
request/response cycle with the following implementation requirements:

1. A member variable must be declared called ``MODEL``, which is equal to a
   subclass (Note: type, not instance) of the base ORM model. The reasons for
   using a subclass is mostly just because different services use different
   incompatible primary identifiers for their repositories. The model
   subclasses are typically only one or two additional variable declarations.

2. A method called ``transport_request`` must be implemented, which takes the
   complete target identifier (e.g., a URL) and tries to request it one time
   using whatever transport protocol is required for interacting with the
   service. It should not attempt to retry on timeouts or do anything else with
   the response (that is already done for you). It should just either return
   the response or raise a ``FetchError`` exception.

3. A method called ``transport_response_to_string`` must be implemented, which
   takes the entire response of the request in (1) and converts it to a string
   for logging purposes.

4. A method called ``transport_quota_check`` must be implemented, which takes
   the entire response of the request in (1) and checks to see if the process
   has run afoul of any query quotas or rate limits. If the service says to
   wait before making more requests, the method should return ``True`` and also
   the number of seconds to wait, otherwise it returns ``False``.

5. A method called ``transport_response_simplified`` must be implemented, which
   also takes the entire response of the request in (1) and converts it to a
   Python list of dicts (one dict for each repository) with keys given
   according to the aforementioned ``MODEL`` class members.

Because 1, 2, 3, and 4 are basically dependent only on the chosen network
protocol, we also have an HTTP mix-in module, which supplements the lister base
and provides default implementations for those methods along with optional
request header injection using the Python Requests library. The
``transport_quota_check`` method as provided follows the IETF standard for
communicating rate limits with `HTTP code 429
<https://tools.ietf.org/html/rfc6585#section-4>`_ which some hosting services
have chosen not to follow, so it's possible that a specific lister will need to
override it.

On top of all of that, we also provide another layer over the base lister class
which adds support for sequentially looping over indices. What are indices?
Well, some services (`BitBucket <https://bitbucket.org/>`_ and GitHub for
example) don't send you the entire list of all of their repositories at once,
because that server response would be unwieldy. Instead they paginate their
results, and they also allow you to query their APIs like this:
``https://server_address.tld/query_type?start_listing_from_id=foo``. Changing
the value of 'foo' lets you fetch a set of repositories starting from there. We
call 'foo' an index, and we call a service that works this way an indexing
service. GitHub uses the repository unique identifier and BitBucket uses the
repository creation time, but a service can really use anything as long as the
values monotonically increase with new repositories. A good indexing service
also includes the URL of the next page with a later 'foo' in its responses. For
these indexing services we provide another intermediate lister called the
indexing lister. Instead of inheriting from :class:`ListerBase
<swh.lister.core.lister_base.ListerBase>`, the lister class would inherit
from :class:`IndexingLister
<swh.lister.core.indexing_lister.IndexingLister>`. Along with the
requirements of the lister base, the indexing lister base adds one extra
requirement:

1. A method called ``get_next_target_from_response`` must be defined, which
   takes a complete request response and returns the index ('foo' above) of the
   next page.

So those are all the basic requirements. There are, of course, a few other
little bits and pieces (covered for now in the code's docstring comments), but
for the most part that's it. It sounds like a lot of information to absorb and
implement, but remember that most of the implementation requirements mentioned
above are already provided for 99% of services by the HTTP mix-in module. It
looks much simpler when we look at the actual implementations of the two
new-style indexing listers we currently have…

When developing a new lister, it's important to test. For this, add the tests
(check `swh/lister/*/tests/`) and register the celery tasks in the main
conftest.py (`swh/lister/core/tests/conftest.py`).

Another important step is to actually run it within the
docker-dev (:ref:`run-lister-tutorial`).

This is the entire source code for the BitBucket repository lister::

    # Copyright (C) 2017 the Software Heritage developers
    # License: GNU General Public License version 3 or later
    # See top-level LICENSE file for more information

    from urllib import parse
    from swh.lister.bitbucket.models import BitBucketModel
    from swh.lister.core.indexing_lister import IndexingHttpLister

    class BitBucketLister(IndexingHttpLister):
        PATH_TEMPLATE = '/repositories?after=%s'
        MODEL = BitBucketModel

        def get_model_from_repo(self, repo):
            return {'uid': repo['uuid'],
                    'indexable': repo['created_on'],
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'html_url': repo['links']['html']['href'],
                    'origin_url': repo['links']['clone'][0]['href'],
                    'origin_type': repo['scm'],
                    'description': repo['description']}

        def get_next_target_from_response(self, response):
            body = response.json()
            if 'next' in body:
                return parse.unquote(body['next'].split('after=')[1])
            else:
                return None

        def transport_response_simplified(self, response):
            repos = response.json()['values']
            return [self.get_model_from_repo(repo) for repo in repos]

And this is the entire source code for the GitHub repository lister::

    # Copyright (C) 2017 the Software Heritage developers
    # License: GNU General Public License version 3 or later
    # See top-level LICENSE file for more information

    import time
    from swh.lister.core.indexing_lister import IndexingHttpLister
    from swh.lister.github.models import GitHubModel

    class GitHubLister(IndexingHttpLister):
	PATH_TEMPLATE = '/repositories?since=%d'
	MODEL = GitHubModel

	def get_model_from_repo(self, repo):
	    return {'uid': repo['id'],
		    'indexable': repo['id'],
		    'name': repo['name'],
		    'full_name': repo['full_name'],
		    'html_url': repo['html_url'],
		    'origin_url': repo['html_url'],
		    'origin_type': 'git',
		    'description': repo['description']}

	def get_next_target_from_response(self, response):
	    if 'next' in response.links:
		next_url = response.links['next']['url']
		return int(next_url.split('since=')[1])
	    else:
		return None

	def transport_response_simplified(self, response):
	    repos = response.json()
	    return [self.get_model_from_repo(repo) for repo in repos]

	def request_headers(self):
	    return {'Accept': 'application/vnd.github.v3+json'}

	def transport_quota_check(self, response):
	    remain = int(response.headers['X-RateLimit-Remaining'])
	    if response.status_code == 403 and remain == 0:
		reset_at = int(response.headers['X-RateLimit-Reset'])
		delay = min(reset_at - time.time(), 3600)
		return True, delay
	    else:
		return False, 0

We can see that there are some common elements:

* Both use the HTTP transport mixin (:class:`IndexingHttpLister
  <swh.lister.core.indexing_lister.IndexingHttpLister>`) just combines
  :class:`ListerHttpTransport
  <swh.lister.core.lister_transports.ListerHttpTransport>` and
  :class:`IndexingLister
  <swh.lister.core.indexing_lister.IndexingLister>`) to get most of the
  network request functionality for free.

* Both also define ``MODEL`` and ``PATH_TEMPLATE`` variables. It should be
  clear to developers that ``PATH_TEMPLATE``, when combined with the base
  service URL (e.g., ``https://some_service.com``) and passed a value (the
  'foo' index described earlier) results in a complete identifier for making
  API requests to these services. It is required by our HTTP module.

* Both services respond using JSON, so both implementations of
  ``transport_response_simplified`` are similar and quite short.

We can also see that there are a few differences:

* GitHub sends the next URL as part of the response header, while BitBucket
  sends it in the response body.

* GitHub differentiates API versions with a request header (our HTTP
  transport mix-in will automatically use any headers provided by an
  optional request_headers method that we implement here), while
  BitBucket has it as part of their base service URL.  BitBucket uses
  the IETF standard HTTP 429 response code for their rate limit
  notifications (the HTTP transport mix-in automatically handles
  that), while GitHub uses their own custom response headers that need
  special treatment.

* But look at them! 58 lines of Python code, combined, to absorb all
  repositories from two of the largest and most influential source code hosting
  services.

Ok, so what is going on behind the scenes?

To trace the operation of the code, let's start with a sample instantiation and
progress from there to see which methods get called when. What follows will be
a series of extremely reductionist pseudocode methods. This is not what the
code actually looks like (it's not even real code), but it does have the same
basic flow. Bear with me while I try to lay out lister operation in a
quasi-linear way…::

    # main task

    ghl = GitHubLister(lister_name='github.com',
		       api_baseurl='https://github.com')
    ghl.run()

⇓ (IndexingLister.run)::

    # IndexingLister.run

    identifier = None
    do
	response, repos = ListerBase.ingest_data(identifier)
	identifier = GitHubLister.get_next_target_from_response(response)
    while(identifier)

⇓ (ListerBase.ingest_data)::

    # ListerBase.ingest_data

    response = ListerBase.safely_issue_request(identifier)
    repos = GitHubLister.transport_response_simplified(response)
    injected = ListerBase.inject_repo_data_into_db(repos)
    return response, injected

⇓ (ListerBase.safely_issue_request)::

    # ListerBase.safely_issue_request

    repeat:
	resp = ListerHttpTransport.transport_request(identifier)
	retry, delay = ListerHttpTransport.transport_quota_check(resp)
	if retry:
	    sleep(delay)
    until((not retry) or too_many_retries)
    return resp

⇓ (ListerHttpTransport.transport_request)::

    # ListerHttpTransport.transport_request

    path = ListerBase.api_baseurl
	 + ListerHttpTransport.PATH_TEMPLATE % identifier
    headers = ListerHttpTransport.request_headers()
    return http.get(path, headers)

(Oh look, there's our ``PATH_TEMPLATE``)

⇓ (ListerHttpTransport.request_headers)::

    # ListerHttpTransport.request_headers

    override → GitHubLister.request_headers

↑↑ (ListerBase.safely_issue_request)

⇓ (ListerHttpTransport.transport_quota_check)::

    # ListerHttpTransport.transport_quota_check

    override → GitHubLister.transport_quota_check

And then we're done. From start to finish, I hope this helps you understand how
the few customized pieces fit into the new shared plumbing.

Now you can go and write up a lister for a code hosting site we don't have yet!
