export PYTHONPATH=`pwd`
dropdb github
createdb github
bin/ghlister createdb
rm cache/*
