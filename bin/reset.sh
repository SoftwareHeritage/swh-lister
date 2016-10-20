# Copyright (C) 2015  Stefano Zacchiroli <zack@upsilon.cc>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

export PYTHONPATH=`pwd`
dropdb github
createdb github
bin/ghlister createdb
rm cache/*
