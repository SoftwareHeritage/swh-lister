# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""
Crates lister
=============

The Crates lister list origins from `Crates.io`_, the Rust community’s crate registry.

Origins are `packages`_ for the `Rust language`_ ecosystem.
Package follow a `layout specifications`_ to be usable with the `Cargo`_ package manager
and have a `Cargo.toml`_ file manifest which consists in metadata to describe and build
a specific package version.

As of August 2022 `Crates.io`_ list 89013 packages name for a total of 588215 released
versions.

Origins retrieving strategy
---------------------------

A json http api to list packages from crates.io exists but we choose a
`different strategy`_ in order to reduce to its bare minimum the amount
of http call and bandwidth.

We download a `db-dump.tar.gz`_ archives which contains csv files as an export of
the crates.io database. Crates.csv list package names, versions.csv list versions
related to package names.
It takes a few seconds to download the archive and parse csv files to build a
full index of existing package and related versions.

The archive also contains a metadata.json file with a timestamp corresponding to
the date the database dump started. The database dump is automatically generated
every 24 hours, around 02:00:00 UTC.

The lister is incremental, so the first time it downloads the db-dump.tar.gz archive as
previously described and store the last seen database dump timestamp.
Next time, it downloads the db-dump.tar.gz but retrieves only the list of new and
changed packages since last seen timestamp with all of their related versions.

Page listing
------------

Each page is related to one package.
Each line of a page corresponds to different versions of this package.

The data schema for each line is:

* **name**: Package name
* **version**: Package version
* **crate_file**: Package download url
* **checksum**: Package download checksum
* **yanked**: Whether the package is yanked or not
* **last_update**: Iso8601 last update

Origins from page
-----------------

The lister yields one origin per page.
The origin url corresponds to the http api url for a package, for example
"https://crates.io/crates/{crate}".

Additionally we add some data for each version, set to "extra_loader_arguments":

* **artifacts**: Represent data about the Crates to download, following
    :ref:`original-artifacts-json specification <extrinsic-metadata-original-artifacts-json>`
* **crates_metadata**: To store all other interesting attributes that do not belongs
    to artifacts. For now it mainly indicate when a version is `yanked`_, and the version
    last_update timestamp.

Origin data example::

    {
        "url": "https://crates.io/api/v1/crates/regex-syntax",
        "artifacts": [
            {
                "version": "0.1.0",
                "checksums": {
                    "sha256": "398952a2f6cd1d22bc1774fd663808e32cf36add0280dee5cdd84a8fff2db944",  # noqa: B950
                },
                "filename": "regex-syntax-0.1.0.crate",
                "url": "https://static.crates.io/crates/regex-syntax/regex-syntax-0.1.0.crate",  # noqa: B950
            },
        ],
        "crates_metadata": [
            {
                "version": "0.1.0",
                "last_update": "2017-11-30 03:37:17.449539",
                "yanked": False,
            },
        ],
    },

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory:

   pytest -s -vv --log-cli-level=DEBUG swh/lister/crates/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment:

   docker compose up -d

Then schedule a crates listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-crates

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _Crates.io: https://crates.io
.. _packages: https://doc.rust-lang.org/book/ch07-01-packages-and-crates.html
.. _Rust language: https://www.rust-lang.org/
.. _layout specifications: https://doc.rust-lang.org/cargo/guide/project-layout.html
.. _Cargo: https://doc.rust-lang.org/cargo/guide/why-cargo-exists.html#enter-cargo
.. _Cargo.toml: https://doc.rust-lang.org/cargo/reference/manifest.html
.. _different strategy: https://crates.io/data-access
.. _yanked: https://doc.rust-lang.org/cargo/reference/publishing.html#cargo-yank
.. _db-dump.tar.gz: https://static.crates.io/db-dump.tar.gz
"""


def register():
    from .lister import CratesLister

    return {
        "lister": CratesLister,
        "task_modules": ["%s.tasks" % __name__],
    }
