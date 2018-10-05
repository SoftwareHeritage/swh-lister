#!/usr/bin/env python3

import os

from setuptools import setup, find_packages


def parse_requirements(name=None):
    if name:
        reqf = 'requirements-%s.txt' % name
    else:
        reqf = 'requirements.txt'

    requirements = []
    if not os.path.exists(reqf):
        return requirements

    with open(reqf) as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            requirements.append(line)
    return requirements


setup(
    name='swh.lister',
    description='Software Heritage GitHub lister',
    author='Software Heritage developers',
    author_email='swh-devel@inria.fr',
    url='https://forge.softwareheritage.org/diffusion/DLSGH/',
    packages=find_packages(),
    scripts=['bin/ghlister'],
    install_requires=parse_requirements() + parse_requirements('swh'),
    test_requires=parse_requirements('test'),
    test_suite='nose.collector',
    setup_requires=['vcversioner'],
    extras_require={'testing': parse_requirements('test')},
    vcversioner={'version_module_paths': ['swh/lister/_version.py']},
    include_package_data=True,
)
