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
