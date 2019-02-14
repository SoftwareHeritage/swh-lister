# Copyright (C) 2015  Stefano Zacchiroli <zack@upsilon.cc>
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from contextlib import contextmanager


@contextmanager
def session_scope(mk_session):
    session = mk_session()
    try:
        yield session
        session.commit()
    except:  # noqa
        session.rollback()
        raise
    finally:
        session.close()
