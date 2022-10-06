#!/bin/bash

# this script requires a PostgreSQL server running on host,
# it enables to generate the rubygems_pgsql_dump.tar file used in tests data
# which contains a very small subset of gems for testing purpose

cd /tmp

# download rubygems load-pg-dump utility script
curl -O https://raw.githubusercontent.com/rubygems/rubygems.org/1c8cf7e079e56f709e7fc8f4b2398637e41815f2/script/load-pg-dump

# download latest rubygems pgsql dump and load rubygems db in local pgsql server
./load-pg-dump -c rubygems_dump.tar

# remove all rows in the rubygems db not related to gem haar_joke or l33tify
# those gems have few releases so that is why they have been picked
# also drop tables not needed by the rubygems lister
cleanup_script=$(cat <<- EOF
with t as (
  select id from rubygems where name = 'haar_joke'
),
t2 as (
  select id from rubygems where name = 'l33tify'
) delete from versions where rubygem_id != (select id from t) and rubygem_id != (select id from t2);

delete from rubygems where name != 'haar_joke' and name != 'l33tify';

drop table dependencies;
drop table gem_downloads;
drop table linksets;
EOF
)
echo $cleanup_script | psql rubygems

# create the rubygems_pgsql_dump.tar file
mkdir -p public_postgresql/databases
pg_dump rubygems | gzip -c > public_postgresql/databases/PostgreSQL.sql.gz
tar -cvf rubygems_pgsql_dump.tar public_postgresql
