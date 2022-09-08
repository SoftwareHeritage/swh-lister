#!/usr/bin/env bash

# Script to generate fake-.tar.gz files and fake http responses for
# archive.archlinux.org and mirror.archlinuxarm.org
# For tests purposes only

set -euo pipefail

# files and directories
mkdir https_archive.archlinux.org
mkdir https_uk.mirror.archlinuxarm.org

mkdir -p tmp_dir/archives/
cd tmp_dir/archives/

mkdir -p core.files
mkdir -p core.files/gzip-1.12-1
mkdir -p core.files/dialog-1:1.3_20220414-1

mkdir -p extra.files
mkdir -p extra.files/mercurial-6.1.2-1
mkdir -p extra.files/libasyncns-0.8+3+g68cd5af-3

mkdir -p community.files
mkdir -p community.files/python-hglib-2.6.2-4
mkdir -p community.files/gnome-code-assistance-3:3.16.1+r14+gaad6437-1

echo -e """%FILENAME%
gzip-1.12-1-x86_64.pkg.tar.zst

%NAME%
gzip

%BASE%
gzip

%VERSION%
1.12-1

%DESC%
GNU compression utility

%GROUPS%
base-devel

%CSIZE%
81552

%ISIZE%
150448

%MD5SUM%
3e72c94305917d00d9e361a687cf0a3e

%SHA256SUM%
0ee561edfbc1c7c6a204f7cfa43437c3362311b4fd09ea0541134aaea3a8cc07

%PGPSIG%
iQIzBAABCgAdFiEE4kC1fixGMLp2ji8m/BtUfI2BcsgFAmJPIMEACgkQ/BtUfI2BcsjDTw//Zzu/G+1B2qKIwqy7s/3WieNflLj8PdroF2V+5/W9O70zY4P3edkzjJVCjp9j8esIwfacDfgJvqpdQE5oBJKrwtp3FHEKSRXYUwkOWeGcxO9F8scRclqPYIybfeD3zp0hL2iXE3x4NOg46znlYXqr19Nnovb0Pf0XQ3x8B8qwk997aUvmJz40iQ31EOuQ/PaxboOdiGPkAfflBYdcoDS2XprT5Po9bNoHen5qdN55eF3mipOVZMiynZoHVwgWT/lVwEuAUMxPMLW/QAHn7UEyWIii+ysUZCECf7sVUHOtdro4Y3bUl85JlyFx113dvJDy7QVX4qh89YFLHb0E3ml64wa+I5/q8Y2l7FRPr07n6yhb+MDQcA9hteDOzYzhT7gThrtJAEVJSHxxlGoC/GHgPTWwc7RD80OUcAiGJBUjxYUOKy/CBJ7H4zaRCa28CWrh7IEqDUu6hrCZQHAzmAYbF8X8BnIAAg7jkH3tlH8zwtw3eFxATWgSWfPFsl7jPdGwSUjmff1YvOCjh8r4YFuqqejZQSsUWnO9vE37DCVod7qSBPLzJOfCyPpSoouDC3p+vxhJ5Da5vkqUJk017QYDcGxMMyS1joAPBzkkesca7Ej+eHovfEA5mMLmRHR7lULPBnMjz9IW2i0MvRPt4m8wlFucUAUsrMiTn0WM+V2k2qI=

%URL%
https://www.gnu.org/software/gzip/

%LICENSE%
GPL3

%ARCH%
x86_64

%BUILDDATE%
1649352820

%PACKAGER%
Levente Polyak <anthraxx@archlinux.org>

%DEPENDS%
glibc
bash
less
""" > core.files/gzip-1.12-1/desc

echo -e """%FILENAME%
dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst

%NAME%
dialog

%BASE%
dialog

%VERSION%
1:1.3_20220414-1

%DESC%
A tool to display dialog boxes from shell scripts

%CSIZE%
203028

%ISIZE%
483988

%MD5SUM%
06407c0cb11c50d7bf83d600f2e8107c

%SHA256SUM%
ef8c8971f591de7db0f455970ef5d81d5aced1ddf139f963f16f6730b1851fa7

%PGPSIG%
iQEzBAABCAAdFiEEhs/8qRjPOvRxR1iAUeixSKmZnDQFAmJaPyAACgkQUeixSKmZnDQvZAf/X3qO7Wg6f+tnQ4qciRcRpegsExNRfKo6S1XhA9C0BC0LJDcTRHG1C7+NVB6dSSL5SdOSVTEACjDc2APppNuPDOxFtzl9doYMHqYTSud2yEUPpE8K+3mhcyHpeOxJC6ZIsQWOjug9FTBwUCUo6s5nHjkmRpsK0zYgK9ezmOSZXlS3QSNRaGbKzn1JM8BOUv5Y29f8nTCXNn1m6RW0yAlyz4rdHDVWfaBFvYL7IC/6uwA+92LB3egyEzYx6uuRvvlBR75Rh+IATBxfwLo1bNNEmFWA/W6vooICjF2E23zk4yaKw08f+V2fjRDn9Hs/i2B4bNNNWeOf5q7j7y5EnBbmeQ==

%URL%
https://invisible-island.net/dialog/

%LICENSE%
LGPL2.1

%ARCH%
x86_64

%BUILDDATE%
1650081535

%PACKAGER%
Evangelos Foutras <foutrelis@archlinux.org>

%PROVIDES%
libdialog.so=15-64

%DEPENDS%
sh
ncurses
""" > core.files/dialog-1:1.3_20220414-1/desc

echo -e """%FILENAME%
mercurial-6.1.2-1-x86_64.pkg.tar.zst

%NAME%
mercurial

%BASE%
mercurial

%VERSION%
6.1.2-1

%DESC%
A scalable distributed SCM tool

%CSIZE%
5034047

%ISIZE%
26912816

%MD5SUM%
037ff48bf6127e9d37ad7da7026a6dc0

%SHA256SUM%
be33e7bf800d1e84714cd40029d103873e65f5a72dea19d6ad935f3439512cf8

%PGPSIG%
iQEzBAABCAAdFiEEFRnVq6Zb9vwrc8dWek52CV2KUuQFAmJ2UgAACgkQek52CV2KUuRecggAo3nP9o1hmew82njxj8i0Nab8Ih2wXfutxDSNjOr5UFH5ei8wD60EU2iyZK0YhXI+cozoRlDI6lIjcvWiDH3s9m09xoCX/HAnPfaWkCo9h8DEQX/qxHKc8o87UPVebkLNqKGSu/xXd+n3A5gVl1pI3+7HpaXwOFuTtSFpb+hQ46kW2of+q1NaMpAsLX68uQ0rfaurvIkLZFZDK4zBnRxHXrPMlnj6KbCy/U3/H/ySQTSdfa3YiFe5KzL5dcbPlryCGC4N+xhEn/PYc7OL5I/1iEY9F4sggZQOUh4wXUkv6hc0Xp6Htp7kMKuJUoPJt8kaeUZnIWkB1CCBP5IxnET7Ag==

%URL%
https://www.mercurial-scm.org/

%LICENSE%
GPL

%ARCH%
x86_64

%BUILDDATE%
1651921313

%PACKAGER%
Antonio Rojas <arojas@archlinux.org>

%DEPENDS%
python

%OPTDEPENDS%
tk: for the hgk GUI

%MAKEDEPENDS%
python-docutils
""" > extra.files/mercurial-6.1.2-1/desc

echo -e """%FILENAME%
libasyncns-0.8+3+g68cd5af-3-x86_64.pkg.tar.zst

%NAME%
libasyncns

%BASE%
libasyncns

%VERSION%
0.8+3+g68cd5af-3

%DESC%
A C library for executing name service queries asynchronously

%CSIZE%
17036

%ISIZE%
48763

%MD5SUM%
0aad62f00eab3d0ec7798cb5b4a6eddd

%SHA256SUM%
a0262e191dd3b00343e79e3521159c963e26b7a438d4cc44137c64cf0da90516

%PGPSIG%
iQIzBAABCAAdFiEEtZcfLFwQqaCMYAMPeGxj8zDXy5IFAl7DmIIACgkQeGxj8zDXy5IE8w/7BRDCV4cdGG/2DK0ezqicrMTmpRjiN0Zh14s39V/wHt4VmU786y0fjR/2UfvxncnDqBTmiPbe6Ilv5vQ/4aHbRObqeVFD76iMKAPmBWLOvI8rGLlZjK9zLOKTHwKb7EBk4D4HrF/zd/c1Mz5rGkF/RAgchDT2G4NTozG3SUA1cL3TWgvPn4CIEeq2XTO01GCqXMiavdSuyAEIzKjc9zNPQ/2N1qQ2zPuzjbkEEk4Tk2ewKUQbKcVYpp+iwxm5sUFqd/mpnT4scve7bsHm0VduZbz5mqz2fg57/RU8qQ6GjLZjEHQGE2B3YUWzZlxN2x4+skXN7CRNmfAVyoe7C6hsED8cyKx+J8V+hk67xeIfEm0KCOhegpL/TM/O7xR9w5y3WFmN0VS96l5do9hZkkzNn7o64hvjtEypo/sCF/46KqHwJNezukbWENIWJcHYu8EqLaZsTFD+vQ8iXk7xy2ocQQTIfFlThNwPG+oGK8holQjOhdn8C+m8mG5QFQmUqhcPch4qRsUq1uY3CFooIX4pRghkIyrFwmwhxiao2HLegKS9v5RqMCGxJ3jPXT0tB7s56fpC3D2moCJtaN+GUsU3YW/a0gHgIhzCC7HJYZ+T+MkG5LW3Lb5swMXa4Qe5GcSzc1w+cpMurQKANGNk382TO5CRmo3e+dO4CLaXmUGOjGw=

%URL%
http://0pointer.de/lennart/projects/libasyncns

%LICENSE%
LGPL

%ARCH%
x86_64

%BUILDDATE%
1589876807

%PACKAGER%
Felix Yan <felixonmars@archlinux.org>

%DEPENDS%
glibc

%MAKEDEPENDS%
git
lynx
""" > extra.files/libasyncns-0.8+3+g68cd5af-3/desc

echo -e """%FILENAME%
python-hglib-2.6.2-4-any.pkg.tar.zst

%NAME%
python-hglib

%BASE%
python-hglib

%VERSION%
2.6.2-4

%DESC%
A library with a fast, convenient interface to Mercurial. It uses Mercurial's command server for communication with hg.

%CSIZE%
44083

%ISIZE%
242821

%MD5SUM%
ecc6598834dc216efd938466a2425eae

%SHA256SUM%
fd273811023e8c58090d65118d27f5c10ad10ea5d1fbdbcf88c730327cea0952

%PGPSIG%
iQEzBAABCAAdFiEEhs/8qRjPOvRxR1iAUeixSKmZnDQFAmGpaF0ACgkQUeixSKmZnDSHMwf/bCyNUXK2BoZfdNe0hTZJ54M9FgMZC81QPINAugjxpwOYd5zK43PB/n1t5rNpC2jy8G8J5Yuq8eJr5aFV9GB/yeDDlf3gqtOHQteYZjl+oGcfqtVF4i6/e4rXd1mvRH7fFxI18rLThL3Pei+cblh6iZ0NVVqbrd2opURuUvAPwYLN+/YNurFNdS5E1K+TDpMaunA9flatLFV6Cqn3kkyWh0aMT4hN0bv2kvS0AnD3iKh7YTeaHvx1y4o33zcVRDjepcV4ywE6wozteM+Xcelu3XUlZC6luNX05XsQ7x3fKJTFmXrz3y7vYwhq427nuyVEE/yujZLOhBIqLl2VGRUBfQ==

%URL%
https://pypi.python.org/pypi/python-hglib

%LICENSE%
MIT

%ARCH%
any

%BUILDDATE%
1638492205

%PACKAGER%
Evangelos Foutras <foutrelis@archlinux.org>

%DEPENDS%
python
mercurial

%CHECKDEPENDS%
python-nose
""" > community.files/python-hglib-2.6.2-4/desc

echo -e """%FILENAME%
gnome-code-assistance-2:3.16.1+14+gaad6437-2-x86_64.pkg.tar.zst

%NAME%
gnome-code-assistance

%BASE%
gnome-code-assistance

%VERSION%
2:3.16.1+14+gaad6437-2

%DESC%
Code assistance services for GNOME

%GROUPS%
gnome-extra

%CSIZE%
1854253

%ISIZE%
6795615

%MD5SUM%
eadcf1a6bb70a3e564f260b7fc58135a

%SHA256SUM%
6fd0c80b63d205a1edf5c39c7a62d16499e802566f2451c2b85cd28c9bc30ec7

%PGPSIG%
iQIzBAABCAAdFiEEtZcfLFwQqaCMYAMPeGxj8zDXy5IFAmGpWGMACgkQeGxj8zDXy5L5FA/8CXB1h17mEitVHfHvtUbQy/5eZ+REzHQzmtk8SJ5oMk9ojxTuQh95M4gEQrp55g/BWxuXSbnCXu8N0SRpaKgX67kqJn3vnoHGnjobr80L7TXqSEtXj15/153VuoFg5atmbsOgIdgkCzhAJJKxIt0nGfPlegLxHIZ7Ig06dzI9dc2W+cKotnWW6QuRn1CYD28ZKvBhMhBmjcDu6Rj1muz5NvO80HABP7+AVRsqd2eGJdoX/BmBBqjEGnPtXE1wY/uCuG+XWLy2MeV5ps4f8LYubNOa0KIutyEe6IX+29aQGhawI2G4d04azoTBZpy6xtocJzyW+P+vTxcv/4jhj5E6v7izJy34LTShnHd5J/UWiXl50HWKjJbVPN4o0rWX3EptDHX0gyj+1lvS5Za12Lyy8oGeID10T7N8mcEVREM8XylKz7O7wSaKKbVOXQVAWZ/mQwk7GuWOgGH/nPtVgyNNdHSh+3urPzhuvMSoytJmRo4FbOyRju1Zb3RbbIDWA04Dh7DLH1CvxZ53JkNt0wHZFVt792hmZ4o/wFMVXoNrUnHuI9G1sT8TcYjSmiXlZ7l5cyLo6AsvsFUY2ZuBNXz+3M3CzGyGoAV0Hi2SYl5FaZHuKoFh+P5Xk5ngm42kyoAiQKfrled3ff5fWXqU0jbGDUte+QuLcsKYKZ20YhjP2nc=

%URL%
https://wiki.gnome.org/Projects/CodeAssistance

%LICENSE%
GPL3

%ARCH%
x86_64

%BUILDDATE%
1638488044

%PACKAGER%
Felix Yan <felixonmars@archlinux.org>

%DEPENDS%
libgee
python-dbus
python-gobject
python-pylint
python-pyflakes
python-pycodestyle
python-lxml
python-simplejson
ruby-dbus
ruby-sass

%OPTDEPENDS%
clang: Assistance for C and C++
gjs: Assistance for JavaScript
go: Assistance for Go

%MAKEDEPENDS%
intltool
gobject-introspection
llvm
clang
gjs
go
gnome-common
git
""" > community.files/gnome-code-assistance-3:3.16.1+r14+gaad6437-1/desc

# Tar archives
tar -czf ../../https_archive.archlinux.org/repos_last_core_os_x86_64_core.files.tar.gz core.files/*
tar -czf ../../https_archive.archlinux.org/repos_last_extra_os_x86_64_extra.files.tar.gz extra.files/*
tar -czf ../../https_archive.archlinux.org/repos_last_community_os_x86_64_community.files.tar.gz community.files/*


# Fixtures for archlinuxarm.org

mkdir -p arm/aarch64/core.files/gzip-1.12-1
mkdir -p arm/armv7h/core.files/gzip-1.12-1

mkdir -p arm/aarch64/extra.files/mercurial-6.1.2-1
mkdir -p arm/armv7h/extra.files/mercurial-6.1.2-1

mkdir -p arm/aarch64/community.files/python-hglib-2.6.2-4
mkdir -p arm/armv7h/community.files/python-hglib-2.6.2-4

echo -e """%FILENAME%
gzip-1.12-1-aarch64.pkg.tar.xz

%NAME%
gzip

%BASE%
gzip

%VERSION%
1.12-1

%DESC%
GNU compression utility

%GROUPS%
base-devel

%CSIZE%
79640

%ISIZE%
162688

%MD5SUM%
97d1e76302213f0499f45aa4a4d329cc

%SHA256SUM%
9065fdaf21dfcac231b0e5977599b37596a0d964f48ec0a6bff628084d636d4c

%PGPSIG%
iQIzBAABCAAdFiEEaLNTfzmjE7PldNBndxk/FSvb5qYFAmJPUuQACgkQdxk/FSvb5qZTvhAAxa3rIyWh/hXRePyAkPKl14YhopF4FDoyoCA9DJBz8bJ0qCe7IE/lCFgIH3CFPOVQxDttxo2q6KHt/Di2P5TYMyXrkoDdB9dwuku0DPIsYzhAp1PVFUTUe599c8rNVGTn/k62WvcK7jxD0p8niHjveVRjwmJ+uZf3a9AGoedNsQN94I/dnWu2ggFUBXF6c77ak78ED7k2xTlBv2fSK9Jkzkcjxtc4kZKjxzF4NVTnNVJkz6UgFUyESausSfE/ub247pdmk0zTHTPodPKtwuECA8ZwsRrETf5if0WjX81E9ox7AtZ7mcBNuZKdeuBaU4WW3sqH60G3t8c3ZmpxzYWJCOdsiUwYkAu6bw7yvEREdm2J6ZZx4CE59b+1hepO8/BKg+Gxe9jNrSaEqug6SaueXO68Gk3uPqVRbgcXNg6TyHEKPcEhBQS8mzpvTomUOt6A9XCiwVVbuyCfltYKxLwQRh1BeWv2Y3KCjkT4oudxWVXW3FxYjFriw+g6RA41MZ9f+jVMr2cE+QidqN/GmuR8RrFQZhJZ9iZx7S4DrPyxLToPPnTIzRuBJKlDXBgEfIB8cbSSDpZU5SfILZYYHfr9j5hYED765t3959pqBqJ9wPJ0qmydGWInM1M2o1lRyEisWtwTHaAv9LSMklSaMCRPIydqnsdjkHPLAUYlE8yTuRE=

%URL%
https://www.gnu.org/software/gzip/

%LICENSE%
GPL3

%ARCH%
aarch64

%BUILDDATE%
1649365694

%PACKAGER%
Arch Linux ARM Build System <builder+seattle@archlinuxarm.org>""" > arm/aarch64/core.files/gzip-1.12-1/desc

echo -e """%FILENAME%
gzip-1.12-1-armv7h.pkg.tar.xz

%NAME%
gzip

%BASE%
gzip

%VERSION%
1.12-1

%DESC%
GNU compression utility

%GROUPS%
base-devel

%CSIZE%
78468

%ISIZE%
153864

%MD5SUM%
490c9e28db91740f1adcea64cb6ec1aa

%SHA256SUM%
4ffc8bbede3bbdd9dd6ad6f85bb689b3f4b985655e56285691db2a1346eaf0e7

%PGPSIG%
iQIzBAABCAAdFiEEaLNTfzmjE7PldNBndxk/FSvb5qYFAmJPUxgACgkQdxk/FSvb5qZZkBAAwllACKZT9wnFxCcPvZGl/fkHzMs0nyWEsP+JbMaQQaKnSmh8DfklBi+V2rBCRAJiDwBhLjxSS+maW3uxbfaMgNGTl3lSlwvfIz9pUl+OxwS4WB3uMZLNvebVuqO9FQIAB+MdT8ZnWRFRlnj1WPGuDndkZDLlmOqNLWNOgkNS2FAXC0s1nKVGOM8Wd2llYlQkqCglVgOcj4PCmkSBX/BtFJ5gUeelATJiaKQSxN8xFaFbYStlzUe6HhE5Ou2wLHE+XYCEFIgvkoTgZ3eZQbQrV7z/hFW1iv+h9RBbEUcFAZGPbemC3C/PDRMJQySucNEsxCn3huI2KYx0RJunKVJ83QSGJr6xYzSZvCckC9LjHL8DnOOgn+bKJGNc+hBA5EH5/otc17Sr1H+mhx54duc5rH/kUxNg8RwsUEMCgeIw3YQnxeN8GVDbHfsshzk2S+dzOsOZwH+Y0BOknXfQYdssKLKHdktfS2G6t3izZqaflOFLXc5429KAAHldJ+NpYpsKPhCMWYEtdD9Cb21FrdePrlA20BTK02v897gw6qu01vDn7S9fKyQDOjTwO9UZB/S3w99srxwZ3MD6EQH4eLyvD7FSNPYlwiB+WNh+J3+9acHHE9iZ4OCyuutBYf9Pjvwiu9dY1PurqNl3Wd++B/MBYoAX2G6hJr8y8bOF1WBvIhQ=

%URL%
https://www.gnu.org/software/gzip/

%LICENSE%
GPL3

%ARCH%
armv7h

%BUILDDATE%
1649365715

%PACKAGER%
Arch Linux ARM Build System <builder+xu4@archlinuxarm.org>""" > arm/armv7h/core.files/gzip-1.12-1/desc

echo -e """%FILENAME%
mercurial-6.1.3-1-aarch64.pkg.tar.xz

%NAME%
mercurial

%BASE%
mercurial

%VERSION%
6.1.3-1

%DESC%
A scalable distributed SCM tool

%CSIZE%
4931228

%ISIZE%
26959193

%MD5SUM%
0464390744f42faba80c323ee7c72406

%SHA256SUM%
635edb47117e7bda0b821d86e61906c802bd880d4a30a64185d9feec1bd25db6

%PGPSIG%
iQIzBAABCAAdFiEEaLNTfzmjE7PldNBndxk/FSvb5qYFAmKZNusACgkQdxk/FSvb5qaIkg/9FuZemlogqBd7AJA2hi9o/jtcX2nj6m12w76PeZXXgZ9//lV+BVb/fjOThz+ndfmGU34vuyfIDrbolajjWcSUtfwlhIohETbrwHfFTNp2GzA4TmKxl1Mw40ibHP+NptgB0i5z+FRUt5RJyfUBokQqSLzcUr5g1XhSmpEBCDC2tR2nZiq4miW4tJIRwM3HBvAJAtdfRGxGi5rs+Qd2hblTRGITfUA1QJxgq6WJjTbuRPb+BN0ohXHMk9GXVQXh0Df8u9WjleQiPT310W/gXNCd9THfYQr2iC1rbd12/oQsgvEelZuN9ZEtzUmFW5KyCjot4uSxj6jV0fa+nxA4Iyqmma2JzUvF9daObxPWbpD3d1Y+i68J/60ekAnN/7cI+YMBjGtCNzJkOW09Hk+gqHe6/ePwejvkvxqENXwLTMBp57Jjg/+RDJ2gvlNfGPskknLqxc6gz59J9fK/ytC9IwTIF54EDPbtAfLcukxG0HKeGZ54bHsE5397UrdqB8auSVsqkZzlauhJs9QaLnbtBBYaFYRgnmRBj3TMYbJRP+1qgxEOQHUOFLwnDGyfOInozxY0pip3GBbICoxFxss39YzeeR4PVqobLWJQq/uNsJhBmVG6dbYGoHsgWHhl2uTalu//mQhMZgcRBRgZ6FqjniSdme/feXMvacHY7n/OrPWiNPY=

%URL%
https://www.mercurial-scm.org/

%LICENSE%
GPL

%ARCH%
aarch64

%BUILDDATE%
1654208118

%PACKAGER%
Arch Linux ARM Build System <builder+n1@archlinuxarm.org>""" > arm/aarch64/extra.files/mercurial-6.1.2-1/desc

echo -e """%FILENAME%
mercurial-6.1.3-1-armv7h.pkg.tar.xz

%NAME%
mercurial

%BASE%
mercurial

%VERSION%
6.1.3-1

%DESC%
A scalable distributed SCM tool

%CSIZE%
4897816

%ISIZE%
26853841

%MD5SUM%
453effa55e32be3ef9de5a58f322b9c4

%SHA256SUM%
c1321de5890a6f53d41c1a5e339733be145221828703f13bccf3e7fc22612396

%PGPSIG%
iQIzBAABCAAdFiEEaLNTfzmjE7PldNBndxk/FSvb5qYFAmKZNpkACgkQdxk/FSvb5qabaw//Z/NRzDzAlQdEYE3sBB6eJSum9HQrUQDHX7c0fl+wyc0sc+thzfUVueQzFi9EkoTZb9zyuTYGt5KPdQ4cAfEj0ikwxDrS1RFzGyre30OgyQfbGMGnC1BQG4TOLWwS+mFn/tMoeriuMtgHoljsbjn+bSI2JONW6U/kf0s726/HDvmKFLyhHsF6ZGlOQC+ASBR84CY496Yc1SJTnQmGaWzDmF2zfK7OxMkVvVJw7Zi0OgF1L+WEIHHgS0T+bYk6rLX3xxgwQ37XczN9+SSFTM77bF1LfJIlLbLspaE6m8EJnpsTnX8nCvGWfbdPhDqGLdVw6hnNMLPFIXxXuY3KgfwGUX1UKxfvHpbjR0uYvW32Xs85lqsHZShtmaWYTJMDjiLht/6d8uAQLPAOjdDneyaCf0XEMHor8yAd9zcVmSgd/s+TJQYtWK9fsl+QVk8WS484iSSRPZFtVzJpqg1TYulaWha6DZCCidVkryStHnoGi+3vti/9FtUs7jn086PzDfugj9DoV7ixJ6edxIgp7r3TYgzzVTHuyhXBOaE0dp+IX3ekcMF7C37qrfS9uVIVVtMYvnQRICULYlB0LLHvrK1+m4z4ETpqNrjNevcUChns24rnJmmdkOEv/pzmAR7oYmX8rFda8wgiYfciBQzi71XcmP/SyIQud3UJUbvZjiTBRGk=

%URL%
https://www.mercurial-scm.org/

%LICENSE%
GPL

%ARCH%
armv7h

%BUILDDATE%
1654207988

%PACKAGER%
Arch Linux ARM Build System <builder+xu2@archlinuxarm.org>""" > arm/armv7h/extra.files/mercurial-6.1.2-1/desc

echo -e """%FILENAME%
python-hglib-2.6.2-4-any.pkg.tar.xz

%NAME%
python-hglib

%BASE%
python-hglib

%VERSION%
2.6.2-4

%DESC%
A library with a fast, convenient interface to Mercurial. It uses Mercurial's command server for communication with hg.

%CSIZE%
41432

%ISIZE%
242769

%MD5SUM%
0f763d5e85c4ffe728153f2836838674

%SHA256SUM%
7a873e20d1822403c8ecf0c790de02439368000e9b1b74881788a9faea8c81b6

%PGPSIG%
iQIzBAABCAAdFiEEaLNTfzmjE7PldNBndxk/FSvb5qYFAmG4xMQACgkQdxk/FSvb5qboEQ/+PMN4p7cUqEuArNug8UW0h8sG8vXJXyjQo3HxdhIswuNItuBiCaTzFRH+M5Dnoh+Jy+9wLvbzqLnPXkOTgFTBakjyZ8Bxkt1lTYUOUmqCaR3s1nqajOqIRKAAjUuh1oIiM8Hyyfsgrd244jPtRFlL3y6RPgjfd8M9euV9WCxIRVR0ztnvLURlE+yyGVjv6g4rfcwcIPEjV3XUKRd8kLyWkBwDMUgM8rbeVLZjKxdAa1N3XTAikgUi7IJDafpC83IfTzWhBQFaIJ0yQG2FE5FSbY6GlpcpAIktXwxCTBEXYVRtl+tQwDVoLqgExVBMvCza9Nsstav1WwgKnqMIc5HwfNhSPjKoLPKERYhGVpKwY0doal0rfr1gFn4ZOE/WBwCrAFscB9MWhZ/WFXQiWrXfl72YCh6fCdZN5S5xdculOebehgmXP409AE9N0VVM0iCOIG1P9YTv9OWr5VZnUpezKMVXztUHmlAXTkN1dCgPiA34OJ4ExlceNMqbb/ltie0dkRiFRnbat0wIt1KXmhcei4qw0IaFbQo/dvFvigUJ21BUTqzC6ktFICdmL8dJeRjfC7ysu1u/uU+Rq60J/vI6DK1R06oJ5wqVumMdGY4NliZDTooV3+s6M3m/hDkx9IKVn6h+bSTkqiEkgDf/AD3xrKWtO15c1xpA6YeFTkEWL/w=

%URL%
https://pypi.python.org/pypi/python-hglib

%LICENSE%
MIT

%ARCH%
any

%BUILDDATE%
1639498940

%PACKAGER%
Arch Linux ARM Build System <builder+seattle@archlinuxarm.org>""" > arm/aarch64/community.files/python-hglib-2.6.2-4/desc

echo -e """%FILENAME%
python-hglib-2.6.2-4-any.pkg.tar.xz

%NAME%
python-hglib

%BASE%
python-hglib

%VERSION%
2.6.2-4

%DESC%
A library with a fast, convenient interface to Mercurial. It uses Mercurial's command server for communication with hg.

%CSIZE%
41408

%ISIZE%
242769

%MD5SUM%
198ef7d6dd40d778a0bf585cce30b1c8

%SHA256SUM%
4b0f51e57f22ddc0dbe308244fc1db85b9e9f721396dbcfbcab38bcb4fe16e10

%PGPSIG%
iQIzBAABCAAdFiEEaLNTfzmjE7PldNBndxk/FSvb5qYFAmG5GNYACgkQdxk/FSvb5qZa6g/7BcAPCxD5zwY2cBVe5XuwzsTU4cDGoPJ8zVmj9NEpKnoheF29Lfs+dibguAzfox110DhJebVVmS6HeFpQ6QUQtNaO4cser5XBGgF5PTVa4y+gKXiHCOuzmp+iEKmt6u5Gp1lDoMRJb+EvkRRMO51DXCODMvZbj32fyfiVNZsZR5nffQbQ0AWiJ+xeYZVD/7i+mj+wDLtG3+r9KoFFV6C+ZU5g3NDKoHLgLVQLStfiQSDVtIjemPp+CwWQ6AUpC7vzxiPg5X5JdWj5hw/9AgVJHMWqa2q2YgDOPQzLBGgFCRRED96IYoc1ID7ZzI4tXZIQ8L9N4NkIVMyNdZzc1G9XiwOpg360nKNqbfp3igN12Lg8wqXeYdYVdh1xoo3mVIiJ0oo7fygQpRk5RU/UHcahaxcCQgeMvivaW3Xjb3BM4iKcKJb8GcSPdndTKzJlKOAUk+lD5rGICO5tLSKzkoQzB+ULDitEBU9E2VJ1KAczd7d6xZ3IqjO9GUhHIVRvlK31hQcBUA9g0bwZciZlv8M1ZqSeoeZ8SXvk57a92tGvqbfrjMqK9j7DXsi5w6CIGunV1ceHoVIxzzCboBYZU0cLkUpL9jzU0YXPN7Y2F2Lkn0/uVa0xd9HwSqVTyR88k4aqoL618hcbVoHh9EziU/Oc+ME4YB1VYH7kj66Ob/9Y9gI=

%URL%
https://pypi.python.org/pypi/python-hglib

%LICENSE%
MIT

%ARCH%
any

%BUILDDATE%
1639520456

%PACKAGER%
Arch Linux ARM Build System <builder+xu1@archlinuxarm.org>
""" > arm/armv7h/community.files/python-hglib-2.6.2-4/desc

# Tar arm indexes to convenient path and filename
tar -czf ../../https_uk.mirror.archlinuxarm.org/aarch64_core_core.files.tar.gz arm/aarch64/core.files/*
tar -czf ../../https_uk.mirror.archlinuxarm.org/aarch64_extra_extra.files.tar.gz arm/aarch64/extra.files/*
tar -czf ../../https_uk.mirror.archlinuxarm.org/aarch64_community_community.files.tar.gz arm/aarch64/community.files/*

tar -czf ../../https_uk.mirror.archlinuxarm.org/armv7h_core_core.files.tar.gz arm/armv7h/core.files/*
tar -czf ../../https_uk.mirror.archlinuxarm.org/armv7h_extra_extra.files.tar.gz arm/armv7h/extra.files/*
tar -czf ../../https_uk.mirror.archlinuxarm.org/armv7h_community_community.files.tar.gz arm/armv7h/community.files/*

# archive.archlinux.org directory listing html responses (to get packages related versions listing)

cd ../../

echo """<html>
<head><title>Index of /packages/g/gzip/</title></head>
<body>
<h1>Index of /packages/g/gzip/</h1><hr><pre><a href="../">../</a>
<a href="gzip-1.10-1-x86_64.pkg.tar.xz">gzip-1.10-1-x86_64.pkg.tar.xz</a>                      30-Dec-2018 18:38     78K
<a href="gzip-1.10-1-x86_64.pkg.tar.xz.sig">gzip-1.10-1-x86_64.pkg.tar.xz.sig</a>                  30-Dec-2018 18:38     558
<a href="gzip-1.10-2-x86_64.pkg.tar.xz">gzip-1.10-2-x86_64.pkg.tar.xz</a>                      06-Oct-2019 16:02     78K
<a href="gzip-1.10-2-x86_64.pkg.tar.xz.sig">gzip-1.10-2-x86_64.pkg.tar.xz.sig</a>                  06-Oct-2019 16:02     558
<a href="gzip-1.10-3-x86_64.pkg.tar.xz">gzip-1.10-3-x86_64.pkg.tar.xz</a>                      13-Nov-2019 15:55     78K
<a href="gzip-1.10-3-x86_64.pkg.tar.xz.sig">gzip-1.10-3-x86_64.pkg.tar.xz.sig</a>                  13-Nov-2019 15:55     566
<a href="gzip-1.11-1-x86_64.pkg.tar.zst">gzip-1.11-1-x86_64.pkg.tar.zst</a>                     04-Sep-2021 02:02     82K
<a href="gzip-1.11-1-x86_64.pkg.tar.zst.sig">gzip-1.11-1-x86_64.pkg.tar.zst.sig</a>                 04-Sep-2021 02:02     558
<a href="gzip-1.12-1-x86_64.pkg.tar.zst">gzip-1.12-1-x86_64.pkg.tar.zst</a>                     07-Apr-2022 17:35     80K
<a href="gzip-1.12-1-x86_64.pkg.tar.zst.sig">gzip-1.12-1-x86_64.pkg.tar.zst.sig</a>                 07-Apr-2022 17:35     566
</pre><hr></body>
</html>""" > https_archive.archlinux.org/packages_g_gzip

echo -e """<html>
<head><title>Index of /packages/d/dialog/</title></head>
<body>
<h1>Index of /packages/d/dialog/</h1><hr><pre><a href="../">../</a>
<a href="dialog-1%3A1.3_20190211-1-x86_64.pkg.tar.xz">dialog-1:1.3_20190211-1-x86_64.pkg.tar.xz</a>          13-Feb-2019 08:36    180K
<a href="dialog-1%3A1.3_20190211-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20190211-1-x86_64.pkg.tar.xz.sig</a>      13-Feb-2019 08:36     310
<a href="dialog-1%3A1.3_20190724-1-x86_64.pkg.tar.xz">dialog-1:1.3_20190724-1-x86_64.pkg.tar.xz</a>          26-Jul-2019 21:39    180K
<a href="dialog-1%3A1.3_20190724-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20190724-1-x86_64.pkg.tar.xz.sig</a>      26-Jul-2019 21:43     310
<a href="dialog-1%3A1.3_20190728-1-x86_64.pkg.tar.xz">dialog-1:1.3_20190728-1-x86_64.pkg.tar.xz</a>          29-Jul-2019 12:10    180K
<a href="dialog-1%3A1.3_20190728-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20190728-1-x86_64.pkg.tar.xz.sig</a>      29-Jul-2019 12:10     310
<a href="dialog-1%3A1.3_20190806-1-x86_64.pkg.tar.xz">dialog-1:1.3_20190806-1-x86_64.pkg.tar.xz</a>          07-Aug-2019 04:19    182K
<a href="dialog-1%3A1.3_20190806-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20190806-1-x86_64.pkg.tar.xz.sig</a>      07-Aug-2019 04:19     310
<a href="dialog-1%3A1.3_20190808-1-x86_64.pkg.tar.xz">dialog-1:1.3_20190808-1-x86_64.pkg.tar.xz</a>          09-Aug-2019 22:49    182K
<a href="dialog-1%3A1.3_20190808-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20190808-1-x86_64.pkg.tar.xz.sig</a>      09-Aug-2019 22:50     310
<a href="dialog-1%3A1.3_20191110-1-x86_64.pkg.tar.xz">dialog-1:1.3_20191110-1-x86_64.pkg.tar.xz</a>          11-Nov-2019 11:15    183K
<a href="dialog-1%3A1.3_20191110-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20191110-1-x86_64.pkg.tar.xz.sig</a>      11-Nov-2019 11:17     310
<a href="dialog-1%3A1.3_20191110-2-x86_64.pkg.tar.xz">dialog-1:1.3_20191110-2-x86_64.pkg.tar.xz</a>          13-Nov-2019 17:40    183K
<a href="dialog-1%3A1.3_20191110-2-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20191110-2-x86_64.pkg.tar.xz.sig</a>      13-Nov-2019 17:41     310
<a href="dialog-1%3A1.3_20191209-1-x86_64.pkg.tar.xz">dialog-1:1.3_20191209-1-x86_64.pkg.tar.xz</a>          10-Dec-2019 09:56    183K
<a href="dialog-1%3A1.3_20191209-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20191209-1-x86_64.pkg.tar.xz.sig</a>      10-Dec-2019 09:57     310
<a href="dialog-1%3A1.3_20191210-1-x86_64.pkg.tar.xz">dialog-1:1.3_20191210-1-x86_64.pkg.tar.xz</a>          12-Dec-2019 15:55    184K
<a href="dialog-1%3A1.3_20191210-1-x86_64.pkg.tar.xz.sig">dialog-1:1.3_20191210-1-x86_64.pkg.tar.xz.sig</a>      12-Dec-2019 15:56     310
<a href="dialog-1%3A1.3_20200228-1-x86_64.pkg.tar.zst">dialog-1:1.3_20200228-1-x86_64.pkg.tar.zst</a>         06-Mar-2020 02:21    196K
<a href="dialog-1%3A1.3_20200228-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20200228-1-x86_64.pkg.tar.zst.sig</a>     06-Mar-2020 02:22     310
<a href="dialog-1%3A1.3_20200327-1-x86_64.pkg.tar.zst">dialog-1:1.3_20200327-1-x86_64.pkg.tar.zst</a>         29-Mar-2020 17:08    196K
<a href="dialog-1%3A1.3_20200327-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20200327-1-x86_64.pkg.tar.zst.sig</a>     29-Mar-2020 17:09     310
<a href="dialog-1%3A1.3_20201126-1-x86_64.pkg.tar.zst">dialog-1:1.3_20201126-1-x86_64.pkg.tar.zst</a>         27-Nov-2020 12:19    199K
<a href="dialog-1%3A1.3_20201126-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20201126-1-x86_64.pkg.tar.zst.sig</a>     27-Nov-2020 12:20     310
<a href="dialog-1%3A1.3_20210117-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210117-1-x86_64.pkg.tar.zst</a>         18-Jan-2021 18:05    200K
<a href="dialog-1%3A1.3_20210117-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210117-1-x86_64.pkg.tar.zst.sig</a>     18-Jan-2021 18:05     310
<a href="dialog-1%3A1.3_20210306-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210306-1-x86_64.pkg.tar.zst</a>         07-Mar-2021 11:40    201K
<a href="dialog-1%3A1.3_20210306-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210306-1-x86_64.pkg.tar.zst.sig</a>     07-Mar-2021 11:41     310
<a href="dialog-1%3A1.3_20210319-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210319-1-x86_64.pkg.tar.zst</a>         20-Mar-2021 00:12    201K
<a href="dialog-1%3A1.3_20210319-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210319-1-x86_64.pkg.tar.zst.sig</a>     20-Mar-2021 00:13     310
<a href="dialog-1%3A1.3_20210324-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210324-1-x86_64.pkg.tar.zst</a>         26-Mar-2021 17:53    201K
<a href="dialog-1%3A1.3_20210324-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210324-1-x86_64.pkg.tar.zst.sig</a>     26-Mar-2021 17:53     310
<a href="dialog-1%3A1.3_20210509-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210509-1-x86_64.pkg.tar.zst</a>         16-May-2021 02:04    198K
<a href="dialog-1%3A1.3_20210509-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210509-1-x86_64.pkg.tar.zst.sig</a>     16-May-2021 02:04     310
<a href="dialog-1%3A1.3_20210530-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210530-1-x86_64.pkg.tar.zst</a>         31-May-2021 14:59    198K
<a href="dialog-1%3A1.3_20210530-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210530-1-x86_64.pkg.tar.zst.sig</a>     31-May-2021 15:00     310
<a href="dialog-1%3A1.3_20210621-1-x86_64.pkg.tar.zst">dialog-1:1.3_20210621-1-x86_64.pkg.tar.zst</a>         23-Jun-2021 02:59    199K
<a href="dialog-1%3A1.3_20210621-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20210621-1-x86_64.pkg.tar.zst.sig</a>     23-Jun-2021 03:00     310
<a href="dialog-1%3A1.3_20211107-1-x86_64.pkg.tar.zst">dialog-1:1.3_20211107-1-x86_64.pkg.tar.zst</a>         09-Nov-2021 14:06    197K
<a href="dialog-1%3A1.3_20211107-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20211107-1-x86_64.pkg.tar.zst.sig</a>     09-Nov-2021 14:13     310
<a href="dialog-1%3A1.3_20211214-1-x86_64.pkg.tar.zst">dialog-1:1.3_20211214-1-x86_64.pkg.tar.zst</a>         14-Dec-2021 09:26    197K
<a href="dialog-1%3A1.3_20211214-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20211214-1-x86_64.pkg.tar.zst.sig</a>     14-Dec-2021 09:27     310
<a href="dialog-1%3A1.3_20220117-1-x86_64.pkg.tar.zst">dialog-1:1.3_20220117-1-x86_64.pkg.tar.zst</a>         19-Jan-2022 09:56    199K
<a href="dialog-1%3A1.3_20220117-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20220117-1-x86_64.pkg.tar.zst.sig</a>     19-Jan-2022 09:56     310
<a href="dialog-1%3A1.3_20220414-1-x86_64.pkg.tar.zst">dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst</a>         16-Apr-2022 03:59    198K
<a href="dialog-1%3A1.3_20220414-1-x86_64.pkg.tar.zst.sig">dialog-1:1.3_20220414-1-x86_64.pkg.tar.zst.sig</a>     16-Apr-2022 03:59     310
</pre><hr></body>
</html>""" > https_archive.archlinux.org/packages_d_dialog

echo -e """
<html>
<head><title>Index of /packages/m/mercurial/</title></head>
<body>
<h1>Index of /packages/m/mercurial/</h1><hr><pre><a href="../">../</a>
<a href="mercurial-4.8.2-1-x86_64.pkg.tar.xz">mercurial-4.8.2-1-x86_64.pkg.tar.xz</a>                15-Jan-2019 20:31      4M
<a href="mercurial-4.8.2-1-x86_64.pkg.tar.xz.sig">mercurial-4.8.2-1-x86_64.pkg.tar.xz.sig</a>            15-Jan-2019 20:31     310
<a href="mercurial-4.9-1-x86_64.pkg.tar.xz">mercurial-4.9-1-x86_64.pkg.tar.xz</a>                  12-Feb-2019 06:15      4M
<a href="mercurial-4.9-1-x86_64.pkg.tar.xz.sig">mercurial-4.9-1-x86_64.pkg.tar.xz.sig</a>              12-Feb-2019 06:15     310
<a href="mercurial-4.9.1-1-x86_64.pkg.tar.xz">mercurial-4.9.1-1-x86_64.pkg.tar.xz</a>                30-Mar-2019 17:40      4M
<a href="mercurial-4.9.1-1-x86_64.pkg.tar.xz.sig">mercurial-4.9.1-1-x86_64.pkg.tar.xz.sig</a>            30-Mar-2019 17:40     310
<a href="mercurial-5.0-1-x86_64.pkg.tar.xz">mercurial-5.0-1-x86_64.pkg.tar.xz</a>                  10-May-2019 08:44      4M
<a href="mercurial-5.0-1-x86_64.pkg.tar.xz.sig">mercurial-5.0-1-x86_64.pkg.tar.xz.sig</a>              10-May-2019 08:44     310
<a href="mercurial-5.0.1-1-x86_64.pkg.tar.xz">mercurial-5.0.1-1-x86_64.pkg.tar.xz</a>                10-Jun-2019 18:05      4M
<a href="mercurial-5.0.1-1-x86_64.pkg.tar.xz.sig">mercurial-5.0.1-1-x86_64.pkg.tar.xz.sig</a>            10-Jun-2019 18:05     310
<a href="mercurial-5.0.2-1-x86_64.pkg.tar.xz">mercurial-5.0.2-1-x86_64.pkg.tar.xz</a>                10-Jul-2019 04:58      4M
<a href="mercurial-5.0.2-1-x86_64.pkg.tar.xz.sig">mercurial-5.0.2-1-x86_64.pkg.tar.xz.sig</a>            10-Jul-2019 04:58     310
<a href="mercurial-5.1-1-x86_64.pkg.tar.xz">mercurial-5.1-1-x86_64.pkg.tar.xz</a>                  17-Aug-2019 19:58      4M
<a href="mercurial-5.1-1-x86_64.pkg.tar.xz.sig">mercurial-5.1-1-x86_64.pkg.tar.xz.sig</a>              17-Aug-2019 19:58     310
<a href="mercurial-5.1.2-1-x86_64.pkg.tar.xz">mercurial-5.1.2-1-x86_64.pkg.tar.xz</a>                08-Oct-2019 08:38      4M
<a href="mercurial-5.1.2-1-x86_64.pkg.tar.xz.sig">mercurial-5.1.2-1-x86_64.pkg.tar.xz.sig</a>            08-Oct-2019 08:38     310
<a href="mercurial-5.2-1-x86_64.pkg.tar.xz">mercurial-5.2-1-x86_64.pkg.tar.xz</a>                  28-Nov-2019 06:41      4M
<a href="mercurial-5.2-1-x86_64.pkg.tar.xz.sig">mercurial-5.2-1-x86_64.pkg.tar.xz.sig</a>              28-Nov-2019 06:41     310
<a href="mercurial-5.2.1-1-x86_64.pkg.tar.zst">mercurial-5.2.1-1-x86_64.pkg.tar.zst</a>               06-Jan-2020 12:35      4M
<a href="mercurial-5.2.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.2.1-1-x86_64.pkg.tar.zst.sig</a>           06-Jan-2020 12:35     310
<a href="mercurial-5.2.2-1-x86_64.pkg.tar.zst">mercurial-5.2.2-1-x86_64.pkg.tar.zst</a>               15-Jan-2020 14:07      5M
<a href="mercurial-5.2.2-1-x86_64.pkg.tar.zst.sig">mercurial-5.2.2-1-x86_64.pkg.tar.zst.sig</a>           15-Jan-2020 14:07     310
<a href="mercurial-5.2.2-2-x86_64.pkg.tar.zst">mercurial-5.2.2-2-x86_64.pkg.tar.zst</a>               30-Jan-2020 20:05      4M
<a href="mercurial-5.2.2-2-x86_64.pkg.tar.zst.sig">mercurial-5.2.2-2-x86_64.pkg.tar.zst.sig</a>           30-Jan-2020 20:05     310
<a href="mercurial-5.3-1-x86_64.pkg.tar.zst">mercurial-5.3-1-x86_64.pkg.tar.zst</a>                 13-Feb-2020 21:40      5M
<a href="mercurial-5.3-1-x86_64.pkg.tar.zst.sig">mercurial-5.3-1-x86_64.pkg.tar.zst.sig</a>             13-Feb-2020 21:40     566
<a href="mercurial-5.3.1-1-x86_64.pkg.tar.zst">mercurial-5.3.1-1-x86_64.pkg.tar.zst</a>               07-Mar-2020 23:58      4M
<a href="mercurial-5.3.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.3.1-1-x86_64.pkg.tar.zst.sig</a>           07-Mar-2020 23:58     310
<a href="mercurial-5.3.2-1-x86_64.pkg.tar.zst">mercurial-5.3.2-1-x86_64.pkg.tar.zst</a>               05-Apr-2020 17:48      4M
<a href="mercurial-5.3.2-1-x86_64.pkg.tar.zst.sig">mercurial-5.3.2-1-x86_64.pkg.tar.zst.sig</a>           05-Apr-2020 17:48     310
<a href="mercurial-5.4-1-x86_64.pkg.tar.zst">mercurial-5.4-1-x86_64.pkg.tar.zst</a>                 10-May-2020 17:19      5M
<a href="mercurial-5.4-1-x86_64.pkg.tar.zst.sig">mercurial-5.4-1-x86_64.pkg.tar.zst.sig</a>             10-May-2020 17:19     310
<a href="mercurial-5.4-2-x86_64.pkg.tar.zst">mercurial-5.4-2-x86_64.pkg.tar.zst</a>                 04-Jun-2020 13:38      5M
<a href="mercurial-5.4-2-x86_64.pkg.tar.zst.sig">mercurial-5.4-2-x86_64.pkg.tar.zst.sig</a>             04-Jun-2020 13:38     310
<a href="mercurial-5.4.1-1-x86_64.pkg.tar.zst">mercurial-5.4.1-1-x86_64.pkg.tar.zst</a>               06-Jun-2020 12:28      5M
<a href="mercurial-5.4.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.4.1-1-x86_64.pkg.tar.zst.sig</a>           06-Jun-2020 12:28     310
<a href="mercurial-5.4.2-1-x86_64.pkg.tar.zst">mercurial-5.4.2-1-x86_64.pkg.tar.zst</a>               02-Jul-2020 21:35      5M
<a href="mercurial-5.4.2-1-x86_64.pkg.tar.zst.sig">mercurial-5.4.2-1-x86_64.pkg.tar.zst.sig</a>           02-Jul-2020 21:35     566
<a href="mercurial-5.5-1-x86_64.pkg.tar.zst">mercurial-5.5-1-x86_64.pkg.tar.zst</a>                 05-Aug-2020 10:39      5M
<a href="mercurial-5.5-1-x86_64.pkg.tar.zst.sig">mercurial-5.5-1-x86_64.pkg.tar.zst.sig</a>             05-Aug-2020 10:39     310
<a href="mercurial-5.5.1-1-x86_64.pkg.tar.zst">mercurial-5.5.1-1-x86_64.pkg.tar.zst</a>               03-Sep-2020 19:05      5M
<a href="mercurial-5.5.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.5.1-1-x86_64.pkg.tar.zst.sig</a>           03-Sep-2020 19:05     310
<a href="mercurial-5.5.2-1-x86_64.pkg.tar.zst">mercurial-5.5.2-1-x86_64.pkg.tar.zst</a>               07-Oct-2020 20:05      5M
<a href="mercurial-5.5.2-1-x86_64.pkg.tar.zst.sig">mercurial-5.5.2-1-x86_64.pkg.tar.zst.sig</a>           07-Oct-2020 20:05     310
<a href="mercurial-5.6-1-x86_64.pkg.tar.zst">mercurial-5.6-1-x86_64.pkg.tar.zst</a>                 03-Nov-2020 17:26      5M
<a href="mercurial-5.6-1-x86_64.pkg.tar.zst.sig">mercurial-5.6-1-x86_64.pkg.tar.zst.sig</a>             03-Nov-2020 17:26     310
<a href="mercurial-5.6-2-x86_64.pkg.tar.zst">mercurial-5.6-2-x86_64.pkg.tar.zst</a>                 09-Nov-2020 16:54      5M
<a href="mercurial-5.6-2-x86_64.pkg.tar.zst.sig">mercurial-5.6-2-x86_64.pkg.tar.zst.sig</a>             09-Nov-2020 16:54     310
<a href="mercurial-5.6-3-x86_64.pkg.tar.zst">mercurial-5.6-3-x86_64.pkg.tar.zst</a>                 11-Nov-2020 15:20      5M
<a href="mercurial-5.6-3-x86_64.pkg.tar.zst.sig">mercurial-5.6-3-x86_64.pkg.tar.zst.sig</a>             11-Nov-2020 15:20     310
<a href="mercurial-5.6.1-1-x86_64.pkg.tar.zst">mercurial-5.6.1-1-x86_64.pkg.tar.zst</a>               05-Dec-2020 12:29      5M
<a href="mercurial-5.6.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.6.1-1-x86_64.pkg.tar.zst.sig</a>           05-Dec-2020 12:29     310
<a href="mercurial-5.7-1-x86_64.pkg.tar.zst">mercurial-5.7-1-x86_64.pkg.tar.zst</a>                 04-Feb-2021 08:41      5M
<a href="mercurial-5.7-1-x86_64.pkg.tar.zst.sig">mercurial-5.7-1-x86_64.pkg.tar.zst.sig</a>             04-Feb-2021 08:41     310
<a href="mercurial-5.7.1-1-x86_64.pkg.tar.zst">mercurial-5.7.1-1-x86_64.pkg.tar.zst</a>               11-Mar-2021 07:51      5M
<a href="mercurial-5.7.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.7.1-1-x86_64.pkg.tar.zst.sig</a>           11-Mar-2021 07:51     310
<a href="mercurial-5.8-1-x86_64.pkg.tar.zst">mercurial-5.8-1-x86_64.pkg.tar.zst</a>                 04-May-2021 17:55      5M
<a href="mercurial-5.8-1-x86_64.pkg.tar.zst.sig">mercurial-5.8-1-x86_64.pkg.tar.zst.sig</a>             04-May-2021 17:55     310
<a href="mercurial-5.8-2-x86_64.pkg.tar.zst">mercurial-5.8-2-x86_64.pkg.tar.zst</a>                 08-May-2021 22:08      5M
<a href="mercurial-5.8-2-x86_64.pkg.tar.zst.sig">mercurial-5.8-2-x86_64.pkg.tar.zst.sig</a>             08-May-2021 22:08     310
<a href="mercurial-5.8.1-1-x86_64.pkg.tar.zst">mercurial-5.8.1-1-x86_64.pkg.tar.zst</a>               13-Jul-2021 07:04      5M
<a href="mercurial-5.8.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.8.1-1-x86_64.pkg.tar.zst.sig</a>           13-Jul-2021 07:04     310
<a href="mercurial-5.9.1-1-x86_64.pkg.tar.zst">mercurial-5.9.1-1-x86_64.pkg.tar.zst</a>               01-Sep-2021 12:48      5M
<a href="mercurial-5.9.1-1-x86_64.pkg.tar.zst.sig">mercurial-5.9.1-1-x86_64.pkg.tar.zst.sig</a>           01-Sep-2021 12:48     310
<a href="mercurial-5.9.1-2-x86_64.pkg.tar.zst">mercurial-5.9.1-2-x86_64.pkg.tar.zst</a>               24-Sep-2021 17:39      5M
<a href="mercurial-5.9.1-2-x86_64.pkg.tar.zst.sig">mercurial-5.9.1-2-x86_64.pkg.tar.zst.sig</a>           24-Sep-2021 17:39     310
<a href="mercurial-5.9.2-1-x86_64.pkg.tar.zst">mercurial-5.9.2-1-x86_64.pkg.tar.zst</a>               07-Oct-2021 21:52      5M
<a href="mercurial-5.9.2-1-x86_64.pkg.tar.zst.sig">mercurial-5.9.2-1-x86_64.pkg.tar.zst.sig</a>           07-Oct-2021 21:52     310
<a href="mercurial-5.9.3-1-x86_64.pkg.tar.zst">mercurial-5.9.3-1-x86_64.pkg.tar.zst</a>               27-Oct-2021 07:20      5M
<a href="mercurial-5.9.3-1-x86_64.pkg.tar.zst.sig">mercurial-5.9.3-1-x86_64.pkg.tar.zst.sig</a>           27-Oct-2021 07:20     310
<a href="mercurial-6.0-1-x86_64.pkg.tar.zst">mercurial-6.0-1-x86_64.pkg.tar.zst</a>                 25-Nov-2021 17:10      5M
<a href="mercurial-6.0-1-x86_64.pkg.tar.zst.sig">mercurial-6.0-1-x86_64.pkg.tar.zst.sig</a>             25-Nov-2021 17:10     310
<a href="mercurial-6.0-2-x86_64.pkg.tar.zst">mercurial-6.0-2-x86_64.pkg.tar.zst</a>                 30-Nov-2021 20:53      5M
<a href="mercurial-6.0-2-x86_64.pkg.tar.zst.sig">mercurial-6.0-2-x86_64.pkg.tar.zst.sig</a>             30-Nov-2021 20:53     310
<a href="mercurial-6.0-3-x86_64.pkg.tar.zst">mercurial-6.0-3-x86_64.pkg.tar.zst</a>                 02-Dec-2021 12:06      5M
<a href="mercurial-6.0-3-x86_64.pkg.tar.zst.sig">mercurial-6.0-3-x86_64.pkg.tar.zst.sig</a>             02-Dec-2021 12:06     310
<a href="mercurial-6.0.1-1-x86_64.pkg.tar.zst">mercurial-6.0.1-1-x86_64.pkg.tar.zst</a>               08-Jan-2022 10:07      5M
<a href="mercurial-6.0.1-1-x86_64.pkg.tar.zst.sig">mercurial-6.0.1-1-x86_64.pkg.tar.zst.sig</a>           08-Jan-2022 10:07     310
<a href="mercurial-6.0.2-1-x86_64.pkg.tar.zst">mercurial-6.0.2-1-x86_64.pkg.tar.zst</a>               03-Feb-2022 13:28      5M
<a href="mercurial-6.0.2-1-x86_64.pkg.tar.zst.sig">mercurial-6.0.2-1-x86_64.pkg.tar.zst.sig</a>           03-Feb-2022 13:28     310
<a href="mercurial-6.0.3-1-x86_64.pkg.tar.zst">mercurial-6.0.3-1-x86_64.pkg.tar.zst</a>               23-Feb-2022 20:50      5M
<a href="mercurial-6.0.3-1-x86_64.pkg.tar.zst.sig">mercurial-6.0.3-1-x86_64.pkg.tar.zst.sig</a>           23-Feb-2022 20:50     310
<a href="mercurial-6.1-1-x86_64.pkg.tar.zst">mercurial-6.1-1-x86_64.pkg.tar.zst</a>                 03-Mar-2022 18:06      5M
<a href="mercurial-6.1-1-x86_64.pkg.tar.zst.sig">mercurial-6.1-1-x86_64.pkg.tar.zst.sig</a>             03-Mar-2022 18:06     310
<a href="mercurial-6.1-2-x86_64.pkg.tar.zst">mercurial-6.1-2-x86_64.pkg.tar.zst</a>                 04-Mar-2022 08:37      5M
<a href="mercurial-6.1-2-x86_64.pkg.tar.zst.sig">mercurial-6.1-2-x86_64.pkg.tar.zst.sig</a>             04-Mar-2022 08:37     310
<a href="mercurial-6.1.1-1-x86_64.pkg.tar.zst">mercurial-6.1.1-1-x86_64.pkg.tar.zst</a>               07-Apr-2022 18:26      5M
<a href="mercurial-6.1.1-1-x86_64.pkg.tar.zst.sig">mercurial-6.1.1-1-x86_64.pkg.tar.zst.sig</a>           07-Apr-2022 18:26     310
<a href="mercurial-6.1.2-1-x86_64.pkg.tar.zst">mercurial-6.1.2-1-x86_64.pkg.tar.zst</a>               07-May-2022 11:03      5M
<a href="mercurial-6.1.2-1-x86_64.pkg.tar.zst.sig">mercurial-6.1.2-1-x86_64.pkg.tar.zst.sig</a>           07-May-2022 11:03     310
</pre><hr></body>
</html>""" > https_archive.archlinux.org/packages_m_mercurial

echo -e """<html>
<head><title>Index of /packages/l/libasyncns/</title></head>
<body>
<h1>Index of /packages/l/libasyncns/</h1><hr><pre><a href="../">../</a>
<a href="libasyncns-0.8%2B3%2Bg68cd5af-2-x86_64.pkg.tar.xz">libasyncns-0.8+3+g68cd5af-2-x86_64.pkg.tar.xz</a>      09-Nov-2018 23:39     16K
<a href="libasyncns-0.8%2B3%2Bg68cd5af-2-x86_64.pkg.tar.xz.sig">libasyncns-0.8+3+g68cd5af-2-x86_64.pkg.tar.xz.sig</a>  09-Nov-2018 23:39     310
<a href="libasyncns-0.8%2B3%2Bg68cd5af-3-x86_64.pkg.tar.zst">libasyncns-0.8+3+g68cd5af-3-x86_64.pkg.tar.zst</a>     19-May-2020 08:28     17K
<a href="libasyncns-0.8%2B3%2Bg68cd5af-3-x86_64.pkg.tar.zst.sig">libasyncns-0.8+3+g68cd5af-3-x86_64.pkg.tar.zst.sig</a> 19-May-2020 08:28     566
<a href="libasyncns-1%3A0.8%2Br3%2Bg68cd5af-1-x86_64.pkg.tar.zst">libasyncns-1:0.8+r3+g68cd5af-1-x86_64.pkg.tar.zst</a>  18-May-2022 17:23     17K
<a href="libasyncns-1%3A0.8%2Br3%2Bg68cd5af-1-x86_64.pkg.tar.zst.sig">libasyncns-1:0.8+r3+g68cd5af-1-x86_64.pkg.tar.z..&gt;</a> 18-May-2022 17:23     141
</pre><hr></body>
</html>""" > https_archive.archlinux.org/packages_l_libasyncns

echo -e """<html>
<head><title>Index of /packages/p/python-hglib/</title></head>
<body>
<h1>Index of /packages/p/python-hglib/</h1><hr><pre><a href="../">../</a>
<a href="python-hglib-2.6.1-3-any.pkg.tar.xz">python-hglib-2.6.1-3-any.pkg.tar.xz</a>                06-Nov-2019 14:08     40K
<a href="python-hglib-2.6.1-3-any.pkg.tar.xz.sig">python-hglib-2.6.1-3-any.pkg.tar.xz.sig</a>            06-Nov-2019 14:08     566
<a href="python-hglib-2.6.2-1-any.pkg.tar.zst">python-hglib-2.6.2-1-any.pkg.tar.zst</a>               19-Nov-2020 22:29     43K
<a href="python-hglib-2.6.2-1-any.pkg.tar.zst.sig">python-hglib-2.6.2-1-any.pkg.tar.zst.sig</a>           19-Nov-2020 22:29     566
<a href="python-hglib-2.6.2-2-any.pkg.tar.zst">python-hglib-2.6.2-2-any.pkg.tar.zst</a>               19-Nov-2020 22:31     43K
<a href="python-hglib-2.6.2-2-any.pkg.tar.zst.sig">python-hglib-2.6.2-2-any.pkg.tar.zst.sig</a>           19-Nov-2020 22:31     566
<a href="python-hglib-2.6.2-3-any.pkg.tar.zst">python-hglib-2.6.2-3-any.pkg.tar.zst</a>               19-Nov-2020 22:35     43K
<a href="python-hglib-2.6.2-3-any.pkg.tar.zst.sig">python-hglib-2.6.2-3-any.pkg.tar.zst.sig</a>           19-Nov-2020 22:35     566
<a href="python-hglib-2.6.2-4-any.pkg.tar.zst">python-hglib-2.6.2-4-any.pkg.tar.zst</a>               03-Dec-2021 00:44     43K
<a href="python-hglib-2.6.2-4-any.pkg.tar.zst.sig">python-hglib-2.6.2-4-any.pkg.tar.zst.sig</a>           03-Dec-2021 00:44     310
</pre><hr></body>
</html>""" > https_archive.archlinux.org/packages_p_python-hglib

echo -e """<html>
<head><title>Index of /packages/g/gnome-code-assistance/</title></head>
<body>
<h1>Index of /packages/g/gnome-code-assistance/</h1><hr><pre><a href="../">../</a>
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-1-x86_64.pkg.tar.xz">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-1-x8..&gt;</a> 10-Nov-2019 20:55      2M
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-1-x86_64.pkg.tar.xz.sig">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-1-x8..&gt;</a> 10-Nov-2019 20:56     310
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-2-x86_64.pkg.tar.zst">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-2-x8..&gt;</a> 28-Mar-2020 15:58      2M
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-2-x86_64.pkg.tar.zst.sig">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-2-x8..&gt;</a> 28-Mar-2020 15:58     310
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-3-x86_64.pkg.tar.zst">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-3-x8..&gt;</a> 05-Jul-2020 15:28      2M
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-3-x86_64.pkg.tar.zst.sig">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-3-x8..&gt;</a> 05-Jul-2020 15:28     590
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-4-x86_64.pkg.tar.zst">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-4-x8..&gt;</a> 12-Nov-2020 17:28      2M
<a href="gnome-code-assistance-1%3A3.16.1%2B15%2Bg0fd8b5f-4-x86_64.pkg.tar.zst.sig">gnome-code-assistance-1:3.16.1+15+g0fd8b5f-4-x8..&gt;</a> 12-Nov-2020 17:29     310
<a href="gnome-code-assistance-2%3A3.16.1%2B14%2Bgaad6437-1-x86_64.pkg.tar.zst">gnome-code-assistance-2:3.16.1+14+gaad6437-1-x8..&gt;</a> 24-Feb-2021 16:30      2M
<a href="gnome-code-assistance-2%3A3.16.1%2B14%2Bgaad6437-1-x86_64.pkg.tar.zst.sig">gnome-code-assistance-2:3.16.1+14+gaad6437-1-x8..&gt;</a> 24-Feb-2021 16:30     141
<a href="gnome-code-assistance-2%3A3.16.1%2B14%2Bgaad6437-2-x86_64.pkg.tar.zst">gnome-code-assistance-2:3.16.1+14+gaad6437-2-x8..&gt;</a> 02-Dec-2021 23:36      2M
<a href="gnome-code-assistance-2%3A3.16.1%2B14%2Bgaad6437-2-x86_64.pkg.tar.zst.sig">gnome-code-assistance-2:3.16.1+14+gaad6437-2-x8..&gt;</a> 02-Dec-2021 23:36     566
<a href="gnome-code-assistance-3.16.1%2B14%2Bgaad6437-1-x86_64.pkg.tar.xz">gnome-code-assistance-3.16.1+14+gaad6437-1-x86_..&gt;</a> 15-Mar-2019 19:23      2M
<a href="gnome-code-assistance-3.16.1%2B14%2Bgaad6437-1-x86_64.pkg.tar.xz.sig">gnome-code-assistance-3.16.1+14+gaad6437-1-x86_..&gt;</a> 15-Mar-2019 19:23     310
<a href="gnome-code-assistance-3.16.1%2B14%2Bgaad6437-2-x86_64.pkg.tar.xz">gnome-code-assistance-3.16.1+14+gaad6437-2-x86_..&gt;</a> 24-Aug-2019 20:05      2M
<a href="gnome-code-assistance-3.16.1%2B14%2Bgaad6437-2-x86_64.pkg.tar.xz.sig">gnome-code-assistance-3.16.1+14+gaad6437-2-x86_..&gt;</a> 24-Aug-2019 20:05     310
<a href="gnome-code-assistance-3.16.1%2B15%2Bgb9ffc4d-1-x86_64.pkg.tar.xz">gnome-code-assistance-3.16.1+15+gb9ffc4d-1-x86_..&gt;</a> 25-Aug-2019 20:55      2M
<a href="gnome-code-assistance-3.16.1%2B15%2Bgb9ffc4d-1-x86_64.pkg.tar.xz.sig">gnome-code-assistance-3.16.1+15+gb9ffc4d-1-x86_..&gt;</a> 25-Aug-2019 20:55     310
<a href="gnome-code-assistance-3%3A3.16.1%2Br14%2Bgaad6437-1-x86_64.pkg.tar.zst">gnome-code-assistance-3:3.16.1+r14+gaad6437-1-x..&gt;</a> 18-May-2022 17:23      2M
<a href="gnome-code-assistance-3%3A3.16.1%2Br14%2Bgaad6437-1-x86_64.pkg.tar.zst.sig">gnome-code-assistance-3:3.16.1+r14+gaad6437-1-x..&gt;</a> 18-May-2022 17:23     141
</pre><hr></body>
</html>""" > https_archive.archlinux.org/packages_g_gnome-code-assistance

# Clean up removing tmp_dir
rm -rf tmp_dir/
