.. _run-lister-tutorial:

Tutorial: run a lister within docker-dev in just a few steps
============================================================

It is a good practice to run your new lister in docker-dev. This provides an almost
production-like environment. Testing the lister in docker dev prior to deployment
reduces the chances of encountering errors when turning it for production.
Here are the steps you need to follow to run a lister within your local environment.


1. You must edit the docker-compose override file (:file:`docker-compose.override.yml`).
   following the sample provided::

        version: '2'

        services:
        swh-lister:
            volumes:
            - "$SWH_ENVIRONMENT_HOME/swh-lister:/src/swh-lister"

   The file named :file:`docker-compose.override.yml` will automatically be loaded by
   ``docker-compose``.Having an override makes it possible to run a docker container
   with some swh packages installed from sources instead of using the latest
   published packages from pypi. For more details, you may refer to README.md
   present in ``swh-docker-dev``.
2. Follow the instruction mentioned under heading **Preparation steps** and
   **Configuration file sample** in README.md of swh-lister.
3. Add in the lister configuration the new ``task_modules`` and ``task_queues``
   entry for the your new lister. You need to amend the docker/conf/lister.yml file to
   add the entries. Here is an example for GNU lister::

    celery:
      task_broker: amqp://guest:guest@amqp//
      task_modules:
        ...
        - swh.lister.gnu.tasks
      task_queues:
        ...
        - swh.lister.gnu.tasks.GNUListerTask

4. Make sure to run ``storage (5002)`` and ``scheduler (5008)`` services locally.
   You may use the following command to run docker::

    ~/swh-environment/swh-docker-dev$ docker-compose up -d

5. Add the lister task-type in the scheduler.  For example, if you want to
   add pypi lister task-type::

    ~/swh-environment$ swh scheduler task-type add list-gnu-full \
        "swh.lister.gnu.tasks.GNUListerTask" "Full GNU lister" \
        --default-interval '1 day' --backoff-factor 1

  You can check all the task-type by::

    ~/swh-environment$swh scheduler task-type list
    Known task types:
    list-bitbucket-incremental:
      Incrementally list BitBucket
    list-cran:
      Full CRAN Lister
    list-debian-distribution:
      List a Debian distribution
    list-github-full:
      Full update of GitHub repos list
    list-github-incremental:
    ...

  If your lister is creating new loading task not yet registered, you need
  to register that task type as well.

6. Run your lister with the help of scheduler cli. You need to add the task in
   the scheduler using its cli. For example, you need to execute this command
   to run gnu lister ::

     ~/swh-environment$ swh scheduler --url http://localhost:5008/ task add \
      list-gnu-full --policy oneshot

After the execution of lister is complete, you can see the loading task created::

    ~/swh-environment/swh-lister$ swh scheduler task list

You can also check the repositories listed by the lister from the scheduler database
in which the lister output is stored. To connect to the database::

    ~/swh-environment/docker$ docker-compose exec swh-scheduler bash -c \
      'psql swh-scheduler -c "select url from listed_origins"'
