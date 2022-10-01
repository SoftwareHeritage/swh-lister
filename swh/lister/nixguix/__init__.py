# Copyright (C) 2022 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""
NixGuix lister
==============

Nix and Guix package managers are among other things (lazy) functional package managers.
We cannot easily parse their source declarations as it would require some involved
computations.

After some discussion and work with both communities, they now expose public manifests
that the lister consumes to extract origins. Be it the `Guix manifest`_ or the `Nixpkgs
manifests`_.

4 kinds of origins are listed:

- main `Guix repository`_ or `Nixpkgs repository`_ which are 'git' repositories
- VCS origins ('git', 'svn', 'hg')
- unique file ('content')
- unique tarball ('directory')

.. _Guix repository: https://git.savannah.gnu.org/cgit/guix.git/
.. _Nixpkgs repository: https://github.com/NixOS/nixpkgs
.. _Guix manifest: https://guix.gnu.org/sources.json
.. _Nixpkgs manifests: https://nix-community.github.io/nixpkgs-swh/sources-unstable-full.json

"""


def register():
    from .lister import NixGuixLister

    return {
        "lister": NixGuixLister,
        "task_modules": [f"{__name__}.tasks"],
    }
