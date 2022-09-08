#!/usr/bin/env bash

# Script to generate fake-crates-repository.tar.gz
# Creates a git repository like https://github.com/rust-lang/crates.io-index
# for tests purposes

set -euo pipefail

# files and directories
mkdir -p tmp_dir/crates.io-index/
cd tmp_dir/crates.io-index/

mkdir -p .dot-dir
touch .dot-dir/empty
mkdir -p ra/nd
mkdir -p re/ge

touch .dot-file
touch config.json

# Init as a git repository
git init
git add .
git commit -m "Init fake crates.io-index repository for tests purpose"

echo '{"name":"rand","vers":"0.1.1","deps":[],"cksum":"48a45b46c2a8c38348adb1205b13c3c5eb0174e0c0fec52cc88e9fb1de14c54d","features":{},"yanked":false}' > ra/nd/rand
git add .
git commit -m " Updating crate rand#0.1.1"

echo '{"name":"rand","vers":"0.1.2","deps":[{"name":"libc","req":"^0.1.1","features":[""],"optional":false,"default_features":true,"target":null,"kind":"normal"},{"name":"log","req":"^0.2.1","features":[""],"optional":false,"default_features":true,"target":null,"kind":"normal"}],"cksum":"6e229ed392842fa93c1d76018d197b7e1b74250532bafb37b0e1d121a92d4cf7","features":{},"yanked":false}' >> ra/nd/rand
git add .
git commit -m " Updating crate rand#0.1.2"

echo '{"name":"regex","vers":"0.1.0","deps":[],"cksum":"f0ff1ca641d3c9a2c30464dac30183a8b91cdcc959d616961be020cdea6255c5","features":{},"yanked":false}' > re/ge/regex
git add .
git commit -m " Updating crate regex#0.1.0"

echo '{"name":"regex","vers":"0.1.1","deps":[{"name":"regex_macros","req":"^0.1.0","features":[""],"optional":false,"default_features":true,"target":null,"kind":"dev"}],"cksum":"a07bef996bd38a73c21a8e345d2c16848b41aa7ec949e2fedffe9edf74cdfb36","features":{},"yanked":false}' >> re/ge/regex
git add .
git commit -m " Updating crate regex#0.1.1"

echo '{"name":"regex","vers":"0.1.2","deps":[{"name":"regex_macros","req":"^0.1.0","features":[""],"optional":false,"default_features":true,"target":null,"kind":"dev"}],"cksum":"343bd0171ee23346506db6f4c64525de6d72f0e8cc533f83aea97f3e7488cbf9","features":{},"yanked":false}' >> re/ge/regex
git add .
git commit -m " Updating crate regex#0.1.2"

echo '{"name":"regex","vers":"0.1.3","deps":[{"name":"regex_macros","req":"^0.1.0","features":[""],"optional":false,"default_features":true,"target":null,"kind":"dev"}],"cksum":"defb220c4054ca1b95fe8b0c9a6e782dda684c1bdf8694df291733ae8a3748e3","features":{},"yanked":false}' >> re/ge/regex
git add .
git commit -m " Updating crate regex#0.1.3"

echo '{"name":"regex-syntax","vers":"0.1.0","deps":[{"name":"rand","req":"^0.3","features":[""],"optional":false,"default_features":true,"target":null,"kind":"dev"},{"name":"quickcheck","req":"^0.2","features":[""],"optional":false,"default_features":true,"target":null,"kind":"dev"}],"cksum":"398952a2f6cd1d22bc1774fd663808e32cf36add0280dee5cdd84a8fff2db944","features":{},"yanked":false}' > re/ge/regex-syntax
git add .
git commit -m " Updating crate regex-syntax#0.1.0"

# Save some space
rm .git/hooks/*.sample

# Compress git directory as a tar.gz archive
cd ../
tar -cvzf fake-crates-repository.tar.gz crates.io-index
mv fake-crates-repository.tar.gz ../

# Clean up tmp_dir
cd ../
rm -rf tmp_dir
