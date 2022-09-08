#!/usr/bin/env bash

# Script to generate packages-meta-v1.json.gz
# files and fake http responses for https_aur.archlinux.org
# For tests purposes only

set -euo pipefail

# files and directories
mkdir https_aur.archlinux.org

mkdir -p tmp_dir/archives/
cd tmp_dir/archives/

echo -e '''[
{"ID":787300,"Name":"tealdeer-git","PackageBaseID":110159,"PackageBase":"tealdeer-git","Version":"r255.30b7c5f-1","Description":"A fast tldr client in Rust.","URL":"https://github.com/dbrgn/tealdeer","NumVotes":11,"Popularity":0.009683,"OutOfDate":null,"Maintainer":"dbrgn","FirstSubmitted":1460795753,"LastModified":1599251812,"URLPath":"/cgit/aur.git/snapshot/tealdeer-git.tar.gz"},
{"ID":860370,"Name":"ibus-git","PackageBaseID":163059,"PackageBase":"ibus-git","Version":"1.5.23+12+gef4c5c7e-1","Description":"Next Generation Input Bus for Linux","URL":"https://github.com/ibus/ibus/wiki","NumVotes":1,"Popularity":0.989573,"OutOfDate":null,"Maintainer":"tallero","FirstSubmitted":1612764731,"LastModified":1612764731,"URLPath":"/cgit/aur.git/snapshot/ibus-git.tar.gz"},
{"ID":1043337,"Name":"libervia-web-hg","PackageBaseID":170485,"PackageBase":"libervia-web-hg","Version":"0.9.0.r1492.3a34d78f2717-1","Description":"Salut à Toi, multi-frontends multi-purposes XMPP client (Web interface)","URL":"http://salut-a-toi.org/","NumVotes":0,"Popularity":0.0,"OutOfDate":null,"Maintainer":"jnanar","FirstSubmitted":1630224837,"LastModified":1645889458,"URLPath":"/cgit/aur.git/snapshot/libervia-web-hg.tar.gz"},
{"ID":1072642,"Name":"hg-evolve","PackageBaseID":135047,"PackageBase":"hg-evolve","Version":"10.5.1-1","Description":"Flexible evolution of Mercurial history","URL":"https://www.mercurial-scm.org/doc/evolution/","NumVotes":6,"Popularity":0.003887,"OutOfDate":null,"Maintainer":"damien-43","FirstSubmitted":1534190432,"LastModified":1651089776,"URLPath":"/cgit/aur.git/snapshot/hg-evolve.tar.gz"}
]''' > packages-meta-v1.json

# Gzip archive
gzip -c packages-meta-v1.json > ../../https_aur.archlinux.org/packages-meta-v1.json.gz

# Clean up removing tmp_dir
cd ../../
rm -rf tmp_dir/
