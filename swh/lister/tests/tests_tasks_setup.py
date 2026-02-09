# Copyright (C) 2026  The Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from importlib import import_module
from pathlib import Path
import pkgutil

import toml

import swh.lister


def test_tasks_registration_and_configuration():
    """Perform some checks to ensure listing tasks:

    * can be registered in scheduler database
    * have function names starting with "list_"
    * have docstrings defined for task functions
    """
    pyproject_toml_path = Path(swh.lister.__path__[0]) / "../../pyproject.toml"
    pyproject_toml_content = pyproject_toml_path.read_text()
    pyproject_toml = toml.loads(pyproject_toml_content)

    workers_conf = pyproject_toml["project"]["entry-points"]["swh.workers"]

    for _, modname, _ in pkgutil.walk_packages(
        swh.lister.__path__, prefix=f"{swh.lister.__name__}."
    ):
        if modname.endswith(".tasks"):
            lister_module = ".".join(modname.split(".")[1:-1]).replace("_", "-")
            assert lister_module in workers_conf, (
                f"{lister_module} entry is missing in section "
                "'project.entry-points.\"swh.workers\"' from the pyproject.toml file "
                "of swh-lister"
            )

            tasks_module = import_module(modname)
            task_functions = [
                x
                for x in dir(tasks_module)
                # not a private function or celery decorator
                if not x.startswith(("_", "shared_task", "group"))
                # is a function
                and hasattr(getattr(tasks_module, x), "__call__")
                # not a class
                and x[0].islower()
            ]
            assert all(
                task_function.startswith("list_") for task_function in task_functions
            ), f"Some listing task function names in module {modname} do not start with 'list_'"
            assert all(
                getattr(tasks_module, task_function).__doc__ is not None
                for task_function in task_functions
            ), (
                f"Some listing task functions from {modname} do not define a docstring but "
                "it is mandatory for tasks registration in scheduler database"
            )
