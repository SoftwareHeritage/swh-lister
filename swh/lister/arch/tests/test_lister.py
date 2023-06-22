# Copyright (C) 2022-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# flake8: noqa: B950

from swh.lister.arch.lister import ArchLister

expected_origins = [
    {
        "url": "https://archlinux.org/packages/core/x86_64/dialog",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20190211-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20190211-1",
                    "filename": "dialog-1:1.3_20190211-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20190724-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20190724-1",
                    "filename": "dialog-1:1.3_20190724-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20190728-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20190728-1",
                    "filename": "dialog-1:1.3_20190728-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20190806-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20190806-1",
                    "filename": "dialog-1:1.3_20190806-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20190808-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20190808-1",
                    "filename": "dialog-1:1.3_20190808-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20191110-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20191110-1",
                    "filename": "dialog-1:1.3_20191110-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20191110-2-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20191110-2",
                    "filename": "dialog-1:1.3_20191110-2-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20191209-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20191209-1",
                    "filename": "dialog-1:1.3_20191209-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20191210-1-x86_64.pkg.tar.xz",
                    "version": "1:1.3_20191210-1",
                    "filename": "dialog-1:1.3_20191210-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20200228-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20200228-1",
                    "filename": "dialog-1:1.3_20200228-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20200327-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20200327-1",
                    "filename": "dialog-1:1.3_20200327-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20201126-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20201126-1",
                    "filename": "dialog-1:1.3_20201126-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210117-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210117-1",
                    "filename": "dialog-1:1.3_20210117-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210306-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210306-1",
                    "filename": "dialog-1:1.3_20210306-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210319-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210319-1",
                    "filename": "dialog-1:1.3_20210319-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210324-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210324-1",
                    "filename": "dialog-1:1.3_20210324-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210509-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210509-1",
                    "filename": "dialog-1:1.3_20210509-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210530-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210530-1",
                    "filename": "dialog-1:1.3_20210530-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20210621-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20210621-1",
                    "filename": "dialog-1:1.3_20210621-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20211107-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20211107-1",
                    "filename": "dialog-1:1.3_20211107-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20211214-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20211214-1",
                    "filename": "dialog-1:1.3_20211214-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20220117-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20220117-1",
                    "filename": "dialog-1:1.3_20220117-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/d/dialog/dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst",
                    "version": "1:1.3_20220414-1",
                    "filename": "dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst",
                    "checksums": {
                        "md5": "06407c0cb11c50d7bf83d600f2e8107c",
                        "sha256": "ef8c8971f591de7db0f455970ef5d81d5aced1ddf139f963f16f6730b1851fa7",
                    },
                },
            ],
            "arch_metadata": [
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20190211-1",
                    "last_modified": "2019-02-13T08:36:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20190724-1",
                    "last_modified": "2019-07-26T21:39:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20190728-1",
                    "last_modified": "2019-07-29T12:10:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20190806-1",
                    "last_modified": "2019-08-07T04:19:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20190808-1",
                    "last_modified": "2019-08-09T22:49:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20191110-1",
                    "last_modified": "2019-11-11T11:15:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20191110-2",
                    "last_modified": "2019-11-13T17:40:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20191209-1",
                    "last_modified": "2019-12-10T09:56:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20191210-1",
                    "last_modified": "2019-12-12T15:55:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20200228-1",
                    "last_modified": "2020-03-06T02:21:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20200327-1",
                    "last_modified": "2020-03-29T17:08:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20201126-1",
                    "last_modified": "2020-11-27T12:19:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210117-1",
                    "last_modified": "2021-01-18T18:05:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210306-1",
                    "last_modified": "2021-03-07T11:40:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210319-1",
                    "last_modified": "2021-03-20T00:12:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210324-1",
                    "last_modified": "2021-03-26T17:53:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210509-1",
                    "last_modified": "2021-05-16T02:04:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210530-1",
                    "last_modified": "2021-05-31T14:59:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20210621-1",
                    "last_modified": "2021-06-23T02:59:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20211107-1",
                    "last_modified": "2021-11-09T14:06:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20211214-1",
                    "last_modified": "2021-12-14T09:26:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20220117-1",
                    "last_modified": "2022-01-19T09:56:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "dialog",
                    "version": "1:1.3_20220414-1",
                    "last_modified": "2022-04-16T03:59:00",
                },
            ],
        },
    },
    {
        "url": "https://archlinux.org/packages/community/x86_64/gnome-code-assistance",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-1:3.16.1+15+g0fd8b5f-1-x86_64.pkg.tar.xz",
                    "version": "1:3.16.1+15+g0fd8b5f-1",
                    "filename": "gnome-code-assistance-1:3.16.1+15+g0fd8b5f-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-1:3.16.1+15+g0fd8b5f-2-x86_64.pkg.tar.zst",
                    "version": "1:3.16.1+15+g0fd8b5f-2",
                    "filename": "gnome-code-assistance-1:3.16.1+15+g0fd8b5f-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-1:3.16.1+15+g0fd8b5f-3-x86_64.pkg.tar.zst",
                    "version": "1:3.16.1+15+g0fd8b5f-3",
                    "filename": "gnome-code-assistance-1:3.16.1+15+g0fd8b5f-3-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-1:3.16.1+15+g0fd8b5f-4-x86_64.pkg.tar.zst",
                    "version": "1:3.16.1+15+g0fd8b5f-4",
                    "filename": "gnome-code-assistance-1:3.16.1+15+g0fd8b5f-4-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-2:3.16.1+14+gaad6437-1-x86_64.pkg.tar.zst",
                    "version": "2:3.16.1+14+gaad6437-1",
                    "filename": "gnome-code-assistance-2:3.16.1+14+gaad6437-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-2:3.16.1+14+gaad6437-2-x86_64.pkg.tar.zst",
                    "version": "2:3.16.1+14+gaad6437-2",
                    "filename": "gnome-code-assistance-2:3.16.1+14+gaad6437-2-x86_64.pkg.tar.zst",
                    "checksums": {
                        "md5": "eadcf1a6bb70a3e564f260b7fc58135a",
                        "sha256": "6fd0c80b63d205a1edf5c39c7a62d16499e802566f2451c2b85cd28c9bc30ec7",
                    },
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-3.16.1+14+gaad6437-1-x86_64.pkg.tar.xz",
                    "version": "3.16.1+14+gaad6437-1",
                    "filename": "gnome-code-assistance-3.16.1+14+gaad6437-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-3.16.1+14+gaad6437-2-x86_64.pkg.tar.xz",
                    "version": "3.16.1+14+gaad6437-2",
                    "filename": "gnome-code-assistance-3.16.1+14+gaad6437-2-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-3.16.1+15+gb9ffc4d-1-x86_64.pkg.tar.xz",
                    "version": "3.16.1+15+gb9ffc4d-1",
                    "filename": "gnome-code-assistance-3.16.1+15+gb9ffc4d-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gnome-code-assistance/gnome-code-assistance-3:3.16.1+r14+gaad6437-1-x86_64.pkg.tar.zst",
                    "version": "3:3.16.1+r14+gaad6437-1",
                    "filename": "gnome-code-assistance-3:3.16.1+r14+gaad6437-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
            ],
            "arch_metadata": [
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "1:3.16.1+15+g0fd8b5f-1",
                    "last_modified": "2019-11-10T20:55:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "1:3.16.1+15+g0fd8b5f-2",
                    "last_modified": "2020-03-28T15:58:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "1:3.16.1+15+g0fd8b5f-3",
                    "last_modified": "2020-07-05T15:28:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "1:3.16.1+15+g0fd8b5f-4",
                    "last_modified": "2020-11-12T17:28:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "2:3.16.1+14+gaad6437-1",
                    "last_modified": "2021-02-24T16:30:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "2:3.16.1+14+gaad6437-2",
                    "last_modified": "2021-12-02T23:36:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "3.16.1+14+gaad6437-1",
                    "last_modified": "2019-03-15T19:23:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "3.16.1+14+gaad6437-2",
                    "last_modified": "2019-08-24T20:05:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "3.16.1+15+gb9ffc4d-1",
                    "last_modified": "2019-08-25T20:55:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "community",
                    "name": "gnome-code-assistance",
                    "version": "3:3.16.1+r14+gaad6437-1",
                    "last_modified": "2022-05-18T17:23:00",
                },
            ],
        },
    },
    {
        "url": "https://archlinux.org/packages/core/x86_64/gzip",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/g/gzip/gzip-1.10-1-x86_64.pkg.tar.xz",
                    "version": "1.10-1",
                    "filename": "gzip-1.10-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gzip/gzip-1.10-2-x86_64.pkg.tar.xz",
                    "version": "1.10-2",
                    "filename": "gzip-1.10-2-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gzip/gzip-1.10-3-x86_64.pkg.tar.xz",
                    "version": "1.10-3",
                    "filename": "gzip-1.10-3-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gzip/gzip-1.11-1-x86_64.pkg.tar.zst",
                    "version": "1.11-1",
                    "filename": "gzip-1.11-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/g/gzip/gzip-1.12-1-x86_64.pkg.tar.zst",
                    "version": "1.12-1",
                    "filename": "gzip-1.12-1-x86_64.pkg.tar.zst",
                    "checksums": {
                        "md5": "3e72c94305917d00d9e361a687cf0a3e",
                        "sha256": "0ee561edfbc1c7c6a204f7cfa43437c3362311b4fd09ea0541134aaea3a8cc07",
                    },
                },
            ],
            "arch_metadata": [
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "gzip",
                    "version": "1.10-1",
                    "last_modified": "2018-12-30T18:38:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "gzip",
                    "version": "1.10-2",
                    "last_modified": "2019-10-06T16:02:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "gzip",
                    "version": "1.10-3",
                    "last_modified": "2019-11-13T15:55:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "gzip",
                    "version": "1.11-1",
                    "last_modified": "2021-09-04T02:02:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "core",
                    "name": "gzip",
                    "version": "1.12-1",
                    "last_modified": "2022-04-07T17:35:00",
                },
            ],
        },
    },
    {
        "url": "https://archlinux.org/packages/extra/x86_64/libasyncns",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/l/libasyncns/libasyncns-0.8+3+g68cd5af-2-x86_64.pkg.tar.xz",
                    "version": "0.8+3+g68cd5af-2",
                    "filename": "libasyncns-0.8+3+g68cd5af-2-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/l/libasyncns/libasyncns-0.8+3+g68cd5af-3-x86_64.pkg.tar.zst",
                    "version": "0.8+3+g68cd5af-3",
                    "filename": "libasyncns-0.8+3+g68cd5af-3-x86_64.pkg.tar.zst",
                    "checksums": {
                        "md5": "0aad62f00eab3d0ec7798cb5b4a6eddd",
                        "sha256": "a0262e191dd3b00343e79e3521159c963e26b7a438d4cc44137c64cf0da90516",
                    },
                },
                {
                    "url": "https://archive.archlinux.org/packages/l/libasyncns/libasyncns-1:0.8+r3+g68cd5af-1-x86_64.pkg.tar.zst",
                    "version": "1:0.8+r3+g68cd5af-1",
                    "filename": "libasyncns-1:0.8+r3+g68cd5af-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
            ],
            "arch_metadata": [
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "libasyncns",
                    "version": "0.8+3+g68cd5af-2",
                    "last_modified": "2018-11-09T23:39:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "libasyncns",
                    "version": "0.8+3+g68cd5af-3",
                    "last_modified": "2020-05-19T08:28:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "libasyncns",
                    "version": "1:0.8+r3+g68cd5af-1",
                    "last_modified": "2022-05-18T17:23:00",
                },
            ],
        },
    },
    {
        "url": "https://archlinux.org/packages/extra/x86_64/mercurial",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-4.8.2-1-x86_64.pkg.tar.xz",
                    "version": "4.8.2-1",
                    "filename": "mercurial-4.8.2-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-4.9-1-x86_64.pkg.tar.xz",
                    "version": "4.9-1",
                    "filename": "mercurial-4.9-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-4.9.1-1-x86_64.pkg.tar.xz",
                    "version": "4.9.1-1",
                    "filename": "mercurial-4.9.1-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.0-1-x86_64.pkg.tar.xz",
                    "version": "5.0-1",
                    "filename": "mercurial-5.0-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.0.1-1-x86_64.pkg.tar.xz",
                    "version": "5.0.1-1",
                    "filename": "mercurial-5.0.1-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.0.2-1-x86_64.pkg.tar.xz",
                    "version": "5.0.2-1",
                    "filename": "mercurial-5.0.2-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.1-1-x86_64.pkg.tar.xz",
                    "version": "5.1-1",
                    "filename": "mercurial-5.1-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.1.2-1-x86_64.pkg.tar.xz",
                    "version": "5.1.2-1",
                    "filename": "mercurial-5.1.2-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.2-1-x86_64.pkg.tar.xz",
                    "version": "5.2-1",
                    "filename": "mercurial-5.2-1-x86_64.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.2.1-1-x86_64.pkg.tar.zst",
                    "version": "5.2.1-1",
                    "filename": "mercurial-5.2.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.2.2-1-x86_64.pkg.tar.zst",
                    "version": "5.2.2-1",
                    "filename": "mercurial-5.2.2-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.2.2-2-x86_64.pkg.tar.zst",
                    "version": "5.2.2-2",
                    "filename": "mercurial-5.2.2-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.3-1-x86_64.pkg.tar.zst",
                    "version": "5.3-1",
                    "filename": "mercurial-5.3-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.3.1-1-x86_64.pkg.tar.zst",
                    "version": "5.3.1-1",
                    "filename": "mercurial-5.3.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.3.2-1-x86_64.pkg.tar.zst",
                    "version": "5.3.2-1",
                    "filename": "mercurial-5.3.2-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.4-1-x86_64.pkg.tar.zst",
                    "version": "5.4-1",
                    "filename": "mercurial-5.4-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.4-2-x86_64.pkg.tar.zst",
                    "version": "5.4-2",
                    "filename": "mercurial-5.4-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.4.1-1-x86_64.pkg.tar.zst",
                    "version": "5.4.1-1",
                    "filename": "mercurial-5.4.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.4.2-1-x86_64.pkg.tar.zst",
                    "version": "5.4.2-1",
                    "filename": "mercurial-5.4.2-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.5-1-x86_64.pkg.tar.zst",
                    "version": "5.5-1",
                    "filename": "mercurial-5.5-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.5.1-1-x86_64.pkg.tar.zst",
                    "version": "5.5.1-1",
                    "filename": "mercurial-5.5.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.5.2-1-x86_64.pkg.tar.zst",
                    "version": "5.5.2-1",
                    "filename": "mercurial-5.5.2-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.6-1-x86_64.pkg.tar.zst",
                    "version": "5.6-1",
                    "filename": "mercurial-5.6-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.6-2-x86_64.pkg.tar.zst",
                    "version": "5.6-2",
                    "filename": "mercurial-5.6-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.6-3-x86_64.pkg.tar.zst",
                    "version": "5.6-3",
                    "filename": "mercurial-5.6-3-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.6.1-1-x86_64.pkg.tar.zst",
                    "version": "5.6.1-1",
                    "filename": "mercurial-5.6.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.7-1-x86_64.pkg.tar.zst",
                    "version": "5.7-1",
                    "filename": "mercurial-5.7-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.7.1-1-x86_64.pkg.tar.zst",
                    "version": "5.7.1-1",
                    "filename": "mercurial-5.7.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.8-1-x86_64.pkg.tar.zst",
                    "version": "5.8-1",
                    "filename": "mercurial-5.8-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.8-2-x86_64.pkg.tar.zst",
                    "version": "5.8-2",
                    "filename": "mercurial-5.8-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.8.1-1-x86_64.pkg.tar.zst",
                    "version": "5.8.1-1",
                    "filename": "mercurial-5.8.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.9.1-1-x86_64.pkg.tar.zst",
                    "version": "5.9.1-1",
                    "filename": "mercurial-5.9.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.9.1-2-x86_64.pkg.tar.zst",
                    "version": "5.9.1-2",
                    "filename": "mercurial-5.9.1-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.9.2-1-x86_64.pkg.tar.zst",
                    "version": "5.9.2-1",
                    "filename": "mercurial-5.9.2-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-5.9.3-1-x86_64.pkg.tar.zst",
                    "version": "5.9.3-1",
                    "filename": "mercurial-5.9.3-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.0-1-x86_64.pkg.tar.zst",
                    "version": "6.0-1",
                    "filename": "mercurial-6.0-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.0-2-x86_64.pkg.tar.zst",
                    "version": "6.0-2",
                    "filename": "mercurial-6.0-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.0-3-x86_64.pkg.tar.zst",
                    "version": "6.0-3",
                    "filename": "mercurial-6.0-3-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.0.1-1-x86_64.pkg.tar.zst",
                    "version": "6.0.1-1",
                    "filename": "mercurial-6.0.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.0.2-1-x86_64.pkg.tar.zst",
                    "version": "6.0.2-1",
                    "filename": "mercurial-6.0.2-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.0.3-1-x86_64.pkg.tar.zst",
                    "version": "6.0.3-1",
                    "filename": "mercurial-6.0.3-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.1-1-x86_64.pkg.tar.zst",
                    "version": "6.1-1",
                    "filename": "mercurial-6.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.1-2-x86_64.pkg.tar.zst",
                    "version": "6.1-2",
                    "filename": "mercurial-6.1-2-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.1.1-1-x86_64.pkg.tar.zst",
                    "version": "6.1.1-1",
                    "filename": "mercurial-6.1.1-1-x86_64.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/m/mercurial/mercurial-6.1.2-1-x86_64.pkg.tar.zst",
                    "version": "6.1.2-1",
                    "filename": "mercurial-6.1.2-1-x86_64.pkg.tar.zst",
                    "checksums": {
                        "md5": "037ff48bf6127e9d37ad7da7026a6dc0",
                        "sha256": "be33e7bf800d1e84714cd40029d103873e65f5a72dea19d6ad935f3439512cf8",
                    },
                },
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
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.0-1",
                    "last_modified": "2019-05-10T08:44:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.0.1-1",
                    "last_modified": "2019-06-10T18:05:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.0.2-1",
                    "last_modified": "2019-07-10T04:58:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.1-1",
                    "last_modified": "2019-08-17T19:58:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.1.2-1",
                    "last_modified": "2019-10-08T08:38:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.2-1",
                    "last_modified": "2019-11-28T06:41:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.2.1-1",
                    "last_modified": "2020-01-06T12:35:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.2.2-1",
                    "last_modified": "2020-01-15T14:07:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.2.2-2",
                    "last_modified": "2020-01-30T20:05:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.3-1",
                    "last_modified": "2020-02-13T21:40:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.3.1-1",
                    "last_modified": "2020-03-07T23:58:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.3.2-1",
                    "last_modified": "2020-04-05T17:48:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.4-1",
                    "last_modified": "2020-05-10T17:19:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.4-2",
                    "last_modified": "2020-06-04T13:38:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.4.1-1",
                    "last_modified": "2020-06-06T12:28:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.4.2-1",
                    "last_modified": "2020-07-02T21:35:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.5-1",
                    "last_modified": "2020-08-05T10:39:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.5.1-1",
                    "last_modified": "2020-09-03T19:05:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.5.2-1",
                    "last_modified": "2020-10-07T20:05:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.6-1",
                    "last_modified": "2020-11-03T17:26:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.6-2",
                    "last_modified": "2020-11-09T16:54:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.6-3",
                    "last_modified": "2020-11-11T15:20:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.6.1-1",
                    "last_modified": "2020-12-05T12:29:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.7-1",
                    "last_modified": "2021-02-04T08:41:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.7.1-1",
                    "last_modified": "2021-03-11T07:51:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.8-1",
                    "last_modified": "2021-05-04T17:55:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.8-2",
                    "last_modified": "2021-05-08T22:08:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.8.1-1",
                    "last_modified": "2021-07-13T07:04:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.9.1-1",
                    "last_modified": "2021-09-01T12:48:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.9.1-2",
                    "last_modified": "2021-09-24T17:39:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.9.2-1",
                    "last_modified": "2021-10-07T21:52:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "5.9.3-1",
                    "last_modified": "2021-10-27T07:20:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.0-1",
                    "last_modified": "2021-11-25T17:10:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.0-2",
                    "last_modified": "2021-11-30T20:53:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.0-3",
                    "last_modified": "2021-12-02T12:06:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.0.1-1",
                    "last_modified": "2022-01-08T10:07:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.0.2-1",
                    "last_modified": "2022-02-03T13:28:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.0.3-1",
                    "last_modified": "2022-02-23T20:50:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.1-1",
                    "last_modified": "2022-03-03T18:06:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.1-2",
                    "last_modified": "2022-03-04T08:37:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.1.1-1",
                    "last_modified": "2022-04-07T18:26:00",
                },
                {
                    "arch": "x86_64",
                    "repo": "extra",
                    "name": "mercurial",
                    "version": "6.1.2-1",
                    "last_modified": "2022-05-07T11:03:00",
                },
            ],
        },
    },
    {
        "url": "https://archlinux.org/packages/community/any/python-hglib",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://archive.archlinux.org/packages/p/python-hglib/python-hglib-2.6.1-3-any.pkg.tar.xz",
                    "version": "2.6.1-3",
                    "filename": "python-hglib-2.6.1-3-any.pkg.tar.xz",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/p/python-hglib/python-hglib-2.6.2-1-any.pkg.tar.zst",
                    "version": "2.6.2-1",
                    "filename": "python-hglib-2.6.2-1-any.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/p/python-hglib/python-hglib-2.6.2-2-any.pkg.tar.zst",
                    "version": "2.6.2-2",
                    "filename": "python-hglib-2.6.2-2-any.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/p/python-hglib/python-hglib-2.6.2-3-any.pkg.tar.zst",
                    "version": "2.6.2-3",
                    "filename": "python-hglib-2.6.2-3-any.pkg.tar.zst",
                    "checksums": {},
                },
                {
                    "url": "https://archive.archlinux.org/packages/p/python-hglib/python-hglib-2.6.2-4-any.pkg.tar.zst",
                    "version": "2.6.2-4",
                    "filename": "python-hglib-2.6.2-4-any.pkg.tar.zst",
                    "checksums": {
                        "md5": "ecc6598834dc216efd938466a2425eae",
                        "sha256": "fd273811023e8c58090d65118d27f5c10ad10ea5d1fbdbcf88c730327cea0952",
                    },
                },
            ],
            "arch_metadata": [
                {
                    "arch": "any",
                    "repo": "community",
                    "name": "python-hglib",
                    "version": "2.6.1-3",
                    "last_modified": "2019-11-06T14:08:00",
                },
                {
                    "arch": "any",
                    "repo": "community",
                    "name": "python-hglib",
                    "version": "2.6.2-1",
                    "last_modified": "2020-11-19T22:29:00",
                },
                {
                    "arch": "any",
                    "repo": "community",
                    "name": "python-hglib",
                    "version": "2.6.2-2",
                    "last_modified": "2020-11-19T22:31:00",
                },
                {
                    "arch": "any",
                    "repo": "community",
                    "name": "python-hglib",
                    "version": "2.6.2-3",
                    "last_modified": "2020-11-19T22:35:00",
                },
                {
                    "arch": "any",
                    "repo": "community",
                    "name": "python-hglib",
                    "version": "2.6.2-4",
                    "last_modified": "2021-12-03T00:44:00",
                },
            ],
        },
    },
    {
        "url": "https://archlinuxarm.org/packages/aarch64/gzip",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://uk.mirror.archlinuxarm.org/aarch64/core/gzip-1.12-1-aarch64.pkg.tar.xz",
                    "version": "1.12-1",
                    "filename": "gzip-1.12-1-aarch64.pkg.tar.xz",
                    "checksums": {
                        "md5": "97d1e76302213f0499f45aa4a4d329cc",
                        "sha256": "9065fdaf21dfcac231b0e5977599b37596a0d964f48ec0a6bff628084d636d4c",
                    },
                }
            ],
            "arch_metadata": [
                {
                    "arch": "aarch64",
                    "name": "gzip",
                    "repo": "core",
                    "version": "1.12-1",
                    "last_modified": "2022-04-07T21:08:14",
                }
            ],
        },
    },
    {
        "url": "https://archlinuxarm.org/packages/aarch64/mercurial",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://uk.mirror.archlinuxarm.org/aarch64/extra/mercurial-6.1.3-1-aarch64.pkg.tar.xz",
                    "version": "6.1.3-1",
                    "filename": "mercurial-6.1.3-1-aarch64.pkg.tar.xz",
                    "checksums": {
                        "md5": "0464390744f42faba80c323ee7c72406",
                        "sha256": "635edb47117e7bda0b821d86e61906c802bd880d4a30a64185d9feec1bd25db6",
                    },
                }
            ],
            "arch_metadata": [
                {
                    "arch": "aarch64",
                    "name": "mercurial",
                    "repo": "extra",
                    "version": "6.1.3-1",
                    "last_modified": "2022-06-02T22:15:18",
                }
            ],
        },
    },
    {
        "url": "https://archlinuxarm.org/packages/any/python-hglib",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://uk.mirror.archlinuxarm.org/any/community/python-hglib-2.6.2-4-any.pkg.tar.xz",
                    "version": "2.6.2-4",
                    "filename": "python-hglib-2.6.2-4-any.pkg.tar.xz",
                    "checksums": {
                        "md5": "0f763d5e85c4ffe728153f2836838674",
                        "sha256": "7a873e20d1822403c8ecf0c790de02439368000e9b1b74881788a9faea8c81b6",
                    },
                }
            ],
            "arch_metadata": [
                {
                    "arch": "any",
                    "name": "python-hglib",
                    "repo": "community",
                    "version": "2.6.2-4",
                    "last_modified": "2021-12-14T16:22:20",
                }
            ],
        },
    },
    {
        "url": "https://archlinuxarm.org/packages/armv7h/gzip",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://uk.mirror.archlinuxarm.org/armv7h/core/gzip-1.12-1-armv7h.pkg.tar.xz",
                    "version": "1.12-1",
                    "filename": "gzip-1.12-1-armv7h.pkg.tar.xz",
                    "checksums": {
                        "md5": "490c9e28db91740f1adcea64cb6ec1aa",
                        "sha256": "4ffc8bbede3bbdd9dd6ad6f85bb689b3f4b985655e56285691db2a1346eaf0e7",
                    },
                }
            ],
            "arch_metadata": [
                {
                    "arch": "armv7h",
                    "name": "gzip",
                    "repo": "core",
                    "version": "1.12-1",
                    "last_modified": "2022-04-07T21:08:35",
                }
            ],
        },
    },
    {
        "url": "https://archlinuxarm.org/packages/armv7h/mercurial",
        "visit_type": "arch",
        "extra_loader_arguments": {
            "artifacts": [
                {
                    "url": "https://uk.mirror.archlinuxarm.org/armv7h/extra/mercurial-6.1.3-1-armv7h.pkg.tar.xz",
                    "version": "6.1.3-1",
                    "filename": "mercurial-6.1.3-1-armv7h.pkg.tar.xz",
                    "checksums": {
                        "md5": "453effa55e32be3ef9de5a58f322b9c4",
                        "sha256": "c1321de5890a6f53d41c1a5e339733be145221828703f13bccf3e7fc22612396",
                    },
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
]


def test_arch_lister(datadir, requests_mock_datadir, swh_scheduler):
    lister = ArchLister(scheduler=swh_scheduler)
    res = lister.run()

    assert res.pages == 9
    assert res.origins == 11

    scheduler_origins = swh_scheduler.get_listed_origins(lister.lister_obj.id).results

    assert [
        (
            scheduled.visit_type,
            scheduled.url,
            scheduled.extra_loader_arguments["artifacts"],
            scheduled.extra_loader_arguments["arch_metadata"],
        )
        for scheduled in sorted(scheduler_origins, key=lambda scheduled: scheduled.url)
    ] == [
        (
            "arch",
            expected["url"],
            expected["extra_loader_arguments"]["artifacts"],
            expected["extra_loader_arguments"]["arch_metadata"],
        )
        for expected in sorted(expected_origins, key=lambda expected: expected["url"])
    ]
