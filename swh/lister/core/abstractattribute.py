# Copyright (C) 2017 the Software Heritage developers
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


class AbstractAttribute:
    """AbstractAttributes in a base class must be overridden by the subclass.

    It's like the :func:`abc.abstractmethod` decorator, but for things that
    are explicitly attributes/properties, not methods, without the need for
    empty method def boilerplate. Like abc.abstractmethod, the class containing
    AbstractAttributes must inherit from :class:`abc.ABC` or use the
    :class:`abc.ABCMeta` metaclass.

    Usage example::

        import abc
        class ClassContainingAnAbstractAttribute(abc.ABC):
            foo: Union[AbstractAttribute, Any] = \
                AbstractAttribute('docstring for foo')

    """

    __isabstractmethod__ = True

    def __init__(self, docstring=None):
        if docstring is not None:
            self.__doc__ = "AbstractAttribute: " + docstring
