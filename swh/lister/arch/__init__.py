# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""
Arch Linux lister
=================

The Arch lister list origins from `archlinux.org`_, the official Arch Linux packages,
and from `archlinuxarm.org`_, the Arch Linux ARM packages, an unofficial port for arm.

Packages are put in three different repositories, `core`, `extra` and `community`.

To manage listing those origins, this lister must be instantiated with a `flavours` dict.

`flavours` default values::

    "official": {
        "archs": ["x86_64"],
        "repos": ["core", "extra", "community"],
        "base_info_url": "https://archlinux.org",
        "base_archive_url": "https://archive.archlinux.org",
        "base_mirror_url": "",
        "base_api_url": "https://archlinux.org",
    },
    "arm": {
        "archs": ["armv7h", "aarch64"],
        "repos": ["core", "extra", "community"],
        "base_info_url": "https://archlinuxarm.org",
        "base_archive_url": "",
        "base_mirror_url": "https://uk.mirror.archlinuxarm.org",
        "base_api_url": "",
    }

From official Arch Linux repositories we can list all packages and all released versions.
They provide an api and archives.

From Arch Linux ARM repositories we can list all packages at their latest versions, they
do not provide api or archives.

As of August 2022 `archlinux.org`_ list 12592 packages and `archlinuxarm.org` 24044 packages.
Please note that those amounts are the total of `regular`_ and `split`_ packages.

Origins retrieving strategy
---------------------------

Download repositories archives as tar.gz files from https://archive.archlinux.org/repos/last/,
extract to a temp directory and then walks through each 'desc' files.
Repository archive index url example for Arch Linux `core repository`_ and Arch
Linux ARM `extra repository`_.

Each 'desc' file describe the latest released version of a package and helps
to build an origin url and `package versions url`_ from where scrapping artifacts metadata
and get a list of versions.

For Arch Linux ARM it follow the same discovery process parsing 'desc' files.
The main difference is that we can't get existing versions of an arm package
because https://archlinuxarm.org does not have an 'archive' website or api.

Page listing
------------

Each page is a list of package belonging to a flavour ('official', 'arm'), and a
repo ('core', 'extra', 'community').

Each line of a page represents an origin url for a package name with related metadata and versions.

Origin url examples:

* **Arch Linux**: https://archlinux.org/packages/extra/x86_64/mercurial
* **Arch Linux ARM**: https://archlinuxarm.org/packages/armv7h/mercurial

The data schema for each line is:

* **name**: Package name
* **version**: Last released package version
* **last_modified**: Iso8601 last modified date from timestamp
* **url**: Origin url
* **data**: Package metadata dict
* **versions**: A list of dict with artifacts metadata for each versions

The data schema for `versions` within a line:

* **name**: Package name
* **version**: Package version
* **repo**: One of core, extra, community
* **arch**: Processor architecture targeted
* **filename**: Filename of the archive to download
* **url**: Package download url
* **last_modified**: Iso8601 last modified date from timestamp, used as publication date
  for this version
* **length**: Length of the archive to download

Origins from page
-----------------

The origin url corresponds to:

* **Arch Linux**: https://archlinux.org/packages/{repo}/{arch}/{name}
* **Arch Linux ARM**: https://archlinuxarm.org/packages/{arch}/{name}

Additionally we add some data set to "extra_loader_arguments":

* **artifacts**: Represent data about the Arch Linux package archive to download,
  following :ref:`original-artifacts-json specification <extrinsic-metadata-original-artifacts-json>`
* **arch_metadata**: To store all other interesting attributes that do not belongs to artifacts.

Origin data example Arch Linux official::

    {
        "url": "https://archlinux.org/packages/extra/x86_64/mercurial",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-4.8.2-1-x86_64.pkg.tar.xz",  # noqa: B950
                    "version": "4.8.2-1",
                    "length": 4000000,
                    "filename": "mercurial-4.8.2-1-x86_64.pkg.tar.xz",
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-4.9-1-x86_64.pkg.tar.xz",  # noqa: B950
                    "version": "4.9-1",
                    "length": 4000000,
                    "filename": "mercurial-4.9-1-x86_64.pkg.tar.xz",
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-4.9.1-1-x86_64.pkg.tar.xz",  # noqa: B950
                    "version": "4.9.1-1",
                    "length": 4000000,
                    "filename": "mercurial-4.9.1-1-x86_64.pkg.tar.xz",
                },
                ...
            ],
            "arch_metadata": [
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "4.8.2-1",
                    "last_modified": "2019-01-15T20:31:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "4.9-1",
                    "last_modified": "2019-02-12T06:15:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "4.9.1-1",
                    "last_modified": "2019-03-30T17:40:00",
                },
            ],
        },
    },

Origin data example Arch Linux ARM::

    {
        "url": "https://archlinuxarm.org/packages/armv7h/mercurial",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://uk.mirror.archlinuxarm.org/armv7h/extra/mercurial-6.1.3-1-armv7h.pkg.tar.xz",  # noqa: B950
                    "length": 4897816,
                    "version": "6.1.3-1",
                    "filename": "mercurial-6.1.3-1-armv7h.pkg.tar.xz",
                }
            ],
            "arch_metadata": [
                {
                    "arch": "armv7h",
                    "name": "mercurial",
                    "repo": "extra",
                    "version": "6.1.3-1",
                    "last_modified": "2022-06-02T22:13:08",
                }
            ],
        },
    },

Running tests
-------------

Activate the virtualenv and run from within swh-lister directory::

   pytest -s -vv --log-cli-level=DEBUG swh/lister/arch/tests

Testing with Docker
-------------------

Change directory to swh/docker then launch the docker environment::

   docker compose up -d

Then schedule an arch listing task::

   docker compose exec swh-scheduler swh scheduler task add -p oneshot list-arch

You can follow lister execution by displaying logs of swh-lister service::

   docker compose logs -f swh-lister

.. _archlinux.org: https://archlinux.org/packages/
.. _archlinuxarm.org: https://archlinuxarm.org/packages/
.. _core repository: https://archive.archlinux.org/repos/last/core/os/x86_64/core.files.tar.gz
.. _extra repository: https://uk.mirror.archlinuxarm.org/armv7h/extra/extra.files.tar.gz
.. _package versions url: https://archive.archlinux.org/packages/m/mercurial/
.. _regular: https://wiki.archlinux.org/title/PKGBUILD#Package_name
.. _split: https://man.archlinux.org/man/PKGBUILD.5#PACKAGE_SPLITTING
"""


def register():
    from .lister import ArchLister

    return {
        "lister": ArchLister,
        "task_modules": ["%s.tasks" % __name__],
    }
