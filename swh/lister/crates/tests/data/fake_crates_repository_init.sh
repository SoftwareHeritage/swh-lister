#!/usr/bin/env bash

# Script to generate db-dump.tar.gz like https://static.crates.io/db-dump.tar.gz
# Creates csv and json files then build the archive for tests purposes
set -euo pipefail

# files and directories for first db dump
mkdir -p https_static.crates.io
mkdir -p tmp_dir/crates.io-db-dump/2022-08-08-020027/
cd tmp_dir/crates.io-db-dump/2022-08-08-020027/
mkdir data

echo -e '''created_at,description,documentation,downloads,homepage,id,max_upload_size,name,readme,repository,updated_at
2015-02-03 06:17:14.147783,"Random number generators and other randomness functionality.",https://docs.rs/rand,139933633,https://rust-random.github.io/book,1339,,rand,,https://github.com/rust-random/rand,2022-02-14 08:37:47.035988
2014-12-13 22:10:11.303311,"An implementation of regular expressions for Rust. This implementation uses finite automata and guarantees linear time matching on all inputs.",https://docs.rs/regex,85620996,https://github.com/rust-lang/regex,545,,regex,,https://github.com/rust-lang/regex,2022-07-05 18:00:33.712885
2015-05-27 23:19:16.839117,"A regular expression parser.",https://docs.rs/regex-syntax,84299774,https://github.com/rust-lang/regex,2233,,regex-syntax,,https://github.com/rust-lang/regex,2022-07-05 17:59:37.238137
''' > data/crates.csv

echo -e '''checksum,crate_id,crate_size,created_at,downloads,features,id,license,links,num,published_by,updated_at,yanked
d879626d5babe4ca6c4ec953d712e28d939672b325a4f9352f28ca3c82568a15,1339,,2014-12-18 06:56:46.88489,845,{},1321,MIT/Apache-2.0,,0.1.3-experimental,,2017-11-30 05:24:37.146115,f
398952a2f6cd1d22bc1774fd663808e32cf36add0280dee5cdd84a8fff2db944,2233,,2015-05-27 23:19:16.848643,1961,{},10855,MIT/Apache-2.0,,0.1.0,,2017-11-30 03:37:17.449539,f
343bd0171ee23346506db6f4c64525de6d72f0e8cc533f83aea97f3e7488cbf9,545,,2014-12-18 06:56:46.88489,845,{},1321,MIT/Apache-2.0,,0.1.2,,2017-11-30 02:29:20.01125,f
6e229ed392842fa93c1d76018d197b7e1b74250532bafb37b0e1d121a92d4cf7,1339,,2015-02-03 11:15:19.001762,8211,{},4371,MIT/Apache-2.0,,0.1.2,,2017-11-30 03:14:27.545115,f
defb220c4054ca1b95fe8b0c9a6e782dda684c1bdf8694df291733ae8a3748e3,545,,2014-12-19 16:16:41.73772,1498,{},1363,MIT/Apache-2.0,,0.1.3,,2017-11-30 02:26:59.236947,f
48a45b46c2a8c38348adb1205b13c3c5eb0174e0c0fec52cc88e9fb1de14c54d,1339,,2015-02-03 06:17:14.169972,7963,{},4362,MIT/Apache-2.0,,0.1.1,,2017-11-30 03:33:14.186028,f
f0ff1ca641d3c9a2c30464dac30183a8b91cdcc959d616961be020cdea6255c5,545,,2014-12-13 22:10:11.329494,3204,{},1100,MIT/Apache-2.0,,0.1.0,,2017-11-30 02:51:27.240551,f
a07bef996bd38a73c21a8e345d2c16848b41aa7ec949e2fedffe9edf74cdfb36,545,,2014-12-15 20:31:48.571836,889,{},1178,MIT/Apache-2.0,,0.1.1,,2017-11-30 03:03:20.143103,f
''' > data/versions.csv

echo -e '''{
  "timestamp": "2022-08-08T02:00:27.645191645Z",
  "crates_io_commit": "3e5f0b4d2a382ac0951898fd257f693734eadee2"
}
''' > metadata.json

cd ../../
tar -czf db-dump.tar.gz -C crates.io-db-dump .

# A second db dump with a new entry and a different timestamp

mkdir -p crates.io-db-dump_visit1
cp -rf crates.io-db-dump/2022-08-08-020027 crates.io-db-dump_visit1/2022-09-05-020027

cd crates.io-db-dump_visit1/2022-09-05-020027/

echo -e '''{
  "timestamp": "2022-09-05T02:00:27.687167108Z",
  "crates_io_commit": "d3652ad81bd8bd837f2d2442ee08484ee5d4bac3"
}
''' > metadata.json

echo -e '''2019-01-08 15:11:01.560092,"A crate for safe and ergonomic pin-projection.",,48353738,,107436,,pin-project,,https://github.com/taiki-e/pin-project,2022-08-15 13:52:11.642129
''' >> data/crates.csv

echo -e '''ad29a609b6bcd67fee905812e544992d216af9d755757c05ed2d0e15a74c6ecc,107436,56972,2022-08-15 13:52:11.642129,580330,{},602929,Apache-2.0 OR MIT,,1.0.12,33035,2022-08-15 13:52:11.642129,f
''' >> data/versions.csv

cd ../../

tar -czf db-dump.tar.gz_visit1 -C crates.io-db-dump_visit1 .

# Move the generated tar.gz archives to a servable directory
mv db-dump.tar.gz ../https_static.crates.io/
mv db-dump.tar.gz_visit1 ../https_static.crates.io/

# Clean up tmp_dir
cd ../
rm -rf tmp_dir
