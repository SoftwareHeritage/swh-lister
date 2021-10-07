.. _save-forge:

Save a forge
============

Assuming the forge's :ref:`listing type is already supported in the
scheduler<register-task-type>`, use ``swh scheduler task add`` command:

::

   swh scheduler --config-file /etc/softwareheritage/scheduler.yml \
     task add [--policy [recurring|oneshot]] <task-type> [param1=value1] [param2=value2]

For example:

-  To add a task requiring no parameters (launchpad lister)

::

   $ swh scheduler --config-file /etc/softwareheritage/scheduler.yml \
     task add list-launchpad-full
   INFO:swh.core.config:Loading config file /etc/softwareheritage/scheduler.yml
   Created 1 tasks

   Task 1240540
     Next run: just now (2020-09-08 13:08:07+00:00)
     Interval: 90 days, 0:00:00
     Type: list-launchpad-full
     Policy: recurring
     Args:
     Keyword args:

-  To add a one-shot task with parameters:

::

   $ swh scheduler --config-file /etc/softwareheritage/scheduler.yml \
     task add --policy oneshot \
     list-gitea-full url=https://codeberg.org/api/v1/ limit=100
   INFO:swh.core.config:Loading config file /etc/softwareheritage/scheduler.yml
   Created 1 tasks

   Task 1240540
     Next run: just now (2020-09-11 14:25:45+00:00)
     Interval: 90 days, 0:00:00
     Type: list-gitea-full
     Policy: oneshot
     Args:
     Keyword args:
       limit: 100
       url: 'https://codeberg.org/api/v1/'

.. _register-task-type:

Register task types to the scheduler
------------------------------------

- To register new task types, ensure you have the code at the required version:

  - docker environment: use :file:`docker-compose.override.yml` with the desired
    :ref:`volume for both lister and scheduler* containers<run-lister-tutorial>`
  - for production/staging, upgrade the swh package first then trigger the cli.

- Use the ``swh scheduler task-type register`` command:

::

   $ swh scheduler --config-file /etc/softwareheritage/scheduler.yml task-type register
   INFO:swh.core.config:Loading config file /etc/softwareheritage/scheduler.yml
   INFO:swh.scheduler.cli.task_type:Loading entrypoint for plugin lister.launchpad
   INFO:swh.scheduler.cli.task_type:Create task type list-launchpad-incremental in scheduler
   INFO:swh.scheduler.cli.task_type:Create task type list-launchpad-full in scheduler
   INFO:swh.scheduler.cli.task_type:Create task type list-launchpad-new in scheduler
   ...


Note: The command is idempotent so it can be executed multiple times.
