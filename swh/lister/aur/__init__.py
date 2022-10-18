# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
AUR (Arch User Repository) lister
=================================

The AUR lister list origins from `aur.archlinux.org`_, the Arch User Repository.
For each package, there is a git repository, we use the git url as origin and the
snapshot url as the artifact for the loader to download.

Each git repository consist of a directory (for which name corresponds to the package name),
and at least two files, .SRCINFO and PKGBUILD which are recipes for building the package.

Each package has a version, the latest one. There isn't any archives of previous versions,
so the lister will always list one version per package.

As of August 2022 `aur.archlinux.org`_ list 84438 packages. Please note that this amount
is the total of `regular`_ and `split`_ packages.
We will archive `regular`  and `split` packages but only their `pkgbase` because that is
the only one that actually has source code.
The packages amount is 78554 after removing the split ones.

Origins retrieving strategy
---------------------------

An rpc api exists but it is recommended to save bandwidth so it's not used. See
`New AUR Metadata Archives`_ for more on this topic.

To get an index of all AUR existing packages we download a `packages-meta-v1.json.gz`_
which contains a json file listing all existing packages definitions.

Each entry describes the latest released version of a package. The origin url
for a package is built using `pkgbase` and corresponds to a git repository.

Note that we list only standard package (when pkgbase equal pkgname), not the ones
belonging to split packages.

It takes only a couple of minutes to download the 7 MB index archive and parses its
content.

Page listing
------------

Each page is related to one package. As its not possible to get all previous
versions, it will always returns one line.

Each page corresponds to a package with a `version`, an `url` for a Git
repository, a `project_url` which represents the upstream project url and
a canonical `snapshot_url` from which a tar.gz archive of the package can
be downloaded.

The data schema for each line is:

* **pkgname**: Package name
* **version**: Package version
* **url**: Git repository url for a package
* **snapshot_url**: Package download url
* **project_url**: Upstream project url if any
* **last_modified**: Iso8601 last update date

Origins from page
-----------------

The lister yields one origin per page.
The origin url corresponds to the git url of a package, for example ``https://aur.archlinux.org/{package}.git``.

Additionally we add some data set to "extra_loader_arguments":

* **artifacts**: Represent data about the Aur package snapshot to download,
  following :ref:`original-artifacts-json specification <extrinsic-metadata-original-artifacts-json>`
* **aur_metadata**: To store all other interesting attributes that do not belongs to artifacts.

Origin data example::

    {
        "visit_type": "aur",
        "url": "https://aur.archlinux.org/hg-evolve.git",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "filename": "hg-evolve.tar.gz",
                    "url": "https://aur.archlinux.org/cgit/aur.git/snapshot/hg-evolve.tar.gz",  # noqa: B950
                    "version": "10.5.1-1",
                }
            ],
            "aur_metadata": [
                {
                    "version": "10.5.1-1",
                    "project_url": "https://www.mercurial-scm.org/doc/evolution/",
                    "last_update": "2022-04-27T20:02:56+00:00",
                    "pkgname": "hg-evolve",
                }
            ],
        },

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/aur/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule an aur listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-aur

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _aur.archlinux.org: https://aur.archlinux.org
.. _New AUR Metadata Archives: https://lists.archlinux.org/pipermail/aur-general/2021-November/036659.html
.. _packages-meta-v1.json.gz: https://aur.archlinux.org/packages-meta-v1.json.gz
.. _regular: https://wiki.archlinux.org/title/PKGBUILD#Package_name
.. _split: https://man.archlinux.org/man/PKGBUILD.5#PACKAGE_SPLITTING
"""


def register():
    from .lister import AurLister

    return {
        "lister": AurLister,
        "task_modules": ["%s.tasks" % __name__],
    }
