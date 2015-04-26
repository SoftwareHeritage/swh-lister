
from contextlib import contextmanager


@contextmanager
def session_scope(mk_session):
    session = mk_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
