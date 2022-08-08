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

A json http api to list packages from crates.io but we choose a `different strategy`_
in order to reduce to its bare minimum the amount of http call and bandwidth.
We clone a git repository which contains a tree of directories whose last child folder
name corresponds to the package name and contains a Cargo.toml file with some json data
to describe all existing versions of the package.
It takes a few seconds to clone the repository and browse it to build a full index of
existing package and related versions.
The lister is incremental, so the first time it clones and browses the repository as
previously described then stores the last seen commit id.
Next time, it retrieves the list of new and changed files since last commit id and
returns new or changed package with all of their related versions.

Note that all Git related operations are done with `Dulwich`_, a Python
implementation of the Git file formats and protocols.

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
* **last_update**: Iso8601 last update date computed upon git commit date of the
    related Cargo.toml file

Origins from page
-----------------

The lister yields one origin per page.
The origin url corresponds to the http api url for a package, for example
"https://crates.io/api/v1/crates/{package}".

Additionally we add some data set to "extra_loader_arguments":

* **artifacts**: Represent data about the Crates to download, following
    :ref:`original-artifacts-json specification <extrinsic-metadata-original-artifacts-json>`
* **crates_metadata**: To store all other interesting attributes that do not belongs
    to artifacts. For now it mainly indicate when a version is `yanked`_.

Origin data example::

    {
        "url": "https://crates.io/api/v1/crates/rand",
        "artifacts": [
            {
                "checksums": {
                    "sha256": "48a45b46c2a8c38348adb1205b13c3c5eb0174e0c0fec52cc88e9fb1de14c54d",  # noqa: B950
                },
                "filename": "rand-0.1.1.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.1.crate",
                "version": "0.1.1",
            },
            {
                "checksums": {
                    "sha256": "6e229ed392842fa93c1d76018d197b7e1b74250532bafb37b0e1d121a92d4cf7",  # noqa: B950
                },
                "filename": "rand-0.1.2.crate",
                "url": "https://static.crates.io/crates/rand/rand-0.1.2.crate",
                "version": "0.1.2",
            },
        ],
        "crates_metadata": [
            {
                "version": "0.1.1",
                "yanked": False,
            },
            {
                "version": "0.1.2",
                "yanked": False,
            },
        ],
    }

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory:

   pytest -s -vv --log-cli-level=DEBUG swh/lister/crates/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment:

   docker-compose up -d

Then connect to the lister:

   docker exec -it docker_swh-lister_1 bash

And run the lister (The output of this listing results in “oneshot” tasks in the scheduler):

   swh lister run -l crates

.. _Crates.io: https://crates.io
.. _packages: https://doc.rust-lang.org/book/ch07-01-packages-and-crates.html
.. _Rust language: https://www.rust-lang.org/
.. _layout specifications: https://doc.rust-lang.org/cargo/guide/project-layout.html
.. _Cargo: https://doc.rust-lang.org/cargo/guide/why-cargo-exists.html#enter-cargo
.. _Cargo.toml: https://doc.rust-lang.org/cargo/reference/manifest.html
.. _different strategy: https://crates.io/data-access
.. _Dulwich: https://www.dulwich.io/
.. _yanked: https://doc.rust-lang.org/cargo/reference/publishing.html#cargo-yank
"""


def register():
    from .lister import CratesLister

    return {
        "lister": CratesLister,
        "task_modules": ["%s.tasks" % __name__],
    }
