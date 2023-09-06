# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import importlib
import inspect
import pkgutil

import pytest


def lister_packages():
    import swh.lister

    return [
        mod.name
        for mod in pkgutil.iter_modules(swh.lister.__path__)
        if mod.ispkg and mod.name != "tests"
    ]


@pytest.mark.parametrize("lister_package", lister_packages())
def test_lister_has_mandatory_parameters(lister_package):
    from swh.lister.pattern import Lister, StatelessLister

    lister_mandatory_params = {
        "scheduler",
        "url",
        "instance",
        "credentials",
        "max_origins_per_page",
        "max_pages",
        "enable_origins",
    }

    lister_module = importlib.import_module(f"swh.lister.{lister_package}.lister")
    lister_module_members = inspect.getmembers(lister_module)
    for name, obj in lister_module_members:
        if (
            inspect.isclass(obj)
            and obj not in (Lister, StatelessLister)
            and issubclass(obj, Lister)
        ):
            lister_params = set(inspect.getfullargspec(getattr(obj, "__init__")).args)

            missing_params = lister_mandatory_params - lister_params

            assert not missing_params, (
                f"swh.lister.{lister_package}.{name} class is missing the following "
                f"parameters in its constructor: {', '.join(missing_params)}.\n"
                "Please add them and transmit them to the base lister class constructor "
                f"to avoid bad surprises when deploying\nthe {lister_package} lister in "
                "staging or production environment."
            )


@pytest.mark.parametrize("lister_package", lister_packages())
def test_lister_package_has_register_function(lister_package):
    lister_module = importlib.import_module(f"swh.lister.{lister_package}")
    assert hasattr(lister_module, "register"), (
        f"swh.lister.{lister_package} module is missing the register function required "
        "to register its celery tasks in scheduler database."
    )
