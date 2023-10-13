#!/usr/bin/env bash

# Script to generate fake-julia-registry-repository.tar.gz
# Creates a git repository like https://github.com/JuliaRegistries/General.git
# for tests purposes

set -euo pipefail

# files and directories for Julia registry repository
mkdir -p tmp_dir/General/
cd tmp_dir/General/

touch Registry.toml

echo -e 'name = "General"
uuid = "23338594-aafe-5451-b93e-139f81909106"
repo = "https://github.com/JuliaRegistries/General.git"

description = """
Official general Julia package registry where people can
register any package they want without too much debate about
naming and without enforced standards on documentation or
testing. We nevertheless encourage documentation, testing and
some amount of consideration when choosing package names.
"""

[packages]' > Registry.toml

# Init as a git repository
# Force author and commit date to be the same
export GIT_AUTHOR_DATE='2001-01-01T17:18:19+00:00'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git init
git add .
git commit -m "Init fake Julia registry repository for tests purpose"

mkdir -p F/Fable

touch F/Fable/Package.toml
touch F/Fable/Versions.toml

echo -e 'name = "Fable"
uuid = "a3ea4736-0a3b-4c29-ac8a-20364318a635"
repo = "https://github.com/leios/Fable.jl.git"
' > F/Fable/Package.toml

echo -e '["0.0.1"]
git-tree-sha1 = "d98ef9a5309f0ec8caaf34bf4cefaf1f1ca525e8"

["0.0.2"]
git-tree-sha1 = "65301af3ab06b04cf8a52cd43b06222bab5249c2"
' > F/Fable/Versions.toml

echo 'a3ea4736-0a3b-4c29-ac8a-20364318a635 = { name = "Fable", path = "F/Fable" }' >> Registry.toml

export GIT_AUTHOR_DATE='2001-01-02T17:18:19+00:00'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git add .
git commit -m "New package: Fable v0.0.2"

mkdir -p O/Oscar

touch O/Oscar/Package.toml
touch O/Oscar/Versions.toml

echo -e 'name = "Oscar"
uuid = "f1435218-dba5-11e9-1e4d-f1a5fab5fc13"
repo = "https://github.com/oscar-system/Oscar.jl.git"
' > O/Oscar/Package.toml

echo -e '["0.2.0"]
git-tree-sha1 = "cda489ed50fbd625d245655ce6e5858c3c21ce12"

["0.3.0"]
git-tree-sha1 = "d62e911d06affb6450a0d059c3432df284a8e3c1"

["0.4.0"]
git-tree-sha1 = "91a9c623da588d5fcfc1f0ce0b3d57a0e35c65d2"

["0.5.0"]
git-tree-sha1 = "5d595e843a71df04da0e8027c4773a158be0c4f4"

["0.5.1"]
git-tree-sha1 = "501602b8c0efc9b4fc6a68d0cb53b9103f736313"

["0.5.2"]
git-tree-sha1 = "aa42d7bc3282e72b1b5c41d518661634cc454de0"

["0.6.0"]
git-tree-sha1 = "a3ca062f1e9ab1728de6af6812c1a09bb527e5ce"

["0.7.0"]
git-tree-sha1 = "185ce4c7b082bf3530940af4954642292da25ff9"

["0.7.1"]
git-tree-sha1 = "26815d2504820400189b2ba822bea2b4c81555d9"

["0.8.0"]
git-tree-sha1 = "25c9620ab9ee15e72b1fea5a903de51088185a7e"

["0.8.1"]
git-tree-sha1 = "53a5c754fbf891bc279040cfb9a2b85c03489f38"

["0.8.2"]
git-tree-sha1 = "cd7595c13e95d810bfd2dd3a96558fb8fd545470"

["0.9.0"]
git-tree-sha1 = "738574ad4cb14da838e3fa5a2bae0c84cca324ed"

["0.10.0"]
git-tree-sha1 = "79e850c5e047754e985c8e0a4220d6f7b1715999"

["0.10.1"]
git-tree-sha1 = "45a146665c899f358c5d24a1551fee8e710285a1"

["0.10.2"]
git-tree-sha1 = "0b127546fd5068de5d161c9ace299cbeb5b8c8b3"

["0.11.0"]
git-tree-sha1 = "001842c060d17eecae8070f8ba8e8163f760722f"

["0.11.1"]
git-tree-sha1 = "3309b97c9327617cd063cc1de5850dc13aad6007"

["0.11.2"]
git-tree-sha1 = "9c2873412042edb336c5347ffa7a9daf29264da8"

["0.11.3"]
git-tree-sha1 = "0c452a18943144989213e2042766371d49505b22"

["0.12.0"]
git-tree-sha1 = "7618e3ba2e9b2ea43ad5d2c809e726a8a9e6e7b1"

["0.12.1"]
git-tree-sha1 = "59619a31c56c9e61b5dabdbd339e30c227c5d13d"
' > O/Oscar/Versions.toml

echo 'f1435218-dba5-11e9-1e4d-f1a5fab5fc13 = { name = "Oscar", path = "O/Oscar" }' >> Registry.toml

export GIT_AUTHOR_DATE='2001-01-03T17:18:19+00:00'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git add .
git commit -m "New package: Oscar v0.12.1"

# Save some space
rm .git/hooks/*.sample

# First Archive
cd ../
tar -czf fake-julia-registry-repository_0.tar.gz General
mv fake-julia-registry-repository_0.tar.gz ../

# Add some more commits and build a second archive for incremental tests purpose
cd General
echo '

["0.13.0"]
git-tree-sha1 = "c090495f818a063ed23d2d911fe74cc4358b5351"
' >> O/Oscar/Versions.toml

# New version, replace previous uuid with a new one
sed -i -e 's/f1435218-dba5-11e9-1e4d-f1a5fab5fc13/a3ea4736-0a3b-4c29-ac8a-20364318a635/g' Registry.toml

export GIT_AUTHOR_DATE='2001-01-04T17:18:19+00:00'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git add .
git commit -m "New version: Oscar v0.13.0"

mkdir -p V/VulkanSpec

touch V/VulkanSpec/Package.toml
touch V/VulkanSpec/Versions.toml

echo 'name = "VulkanSpec"
uuid = "99a7788f-8f0f-454f-8f6c-c6cf389551ae"
repo = "https://github.com/serenity4/VulkanSpec.jl.git"
' > V/VulkanSpec/Package.toml

echo '["0.1.0"]
git-tree-sha1 = "b5fef67130191c797007a1484f4dc6bfc840caa2"
' > V/VulkanSpec/Versions.toml

echo '99a7788f-8f0f-454f-8f6c-c6cf389551ae = { name = "VulkanSpec", path = "V/VulkanSpec" }' >> Registry.toml

export GIT_AUTHOR_DATE='2001-01-05T17:18:19+00:00'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git add .
git commit -m "New package: VulkanSpec v0.1.0"

# Second Archive
cd ../
tar -czf fake-julia-registry-repository_1.tar.gz General
mv fake-julia-registry-repository_1.tar.gz ../

# Clean up tmp_dir
cd ../
rm -rf tmp_dir
