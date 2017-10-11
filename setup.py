#!/usr/bin/env python3

from setuptools import setup


def parse_requirements():
    requirements = []
    for reqf in ('requirements.txt', 'requirements-swh.txt'):
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
    packages=['swh.lister'],
    scripts=['bin/ghlister'],
    install_requires=parse_requirements(),
    setup_requires=['vcversioner'],
    vcversioner={'version_module_paths': ['swh/lister/_version.py']},
    include_package_data=True,
)
