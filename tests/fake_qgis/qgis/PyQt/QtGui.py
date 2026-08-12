"""Fake qgis.PyQt.QtGui -- QKeySequence and QIcon, as used by core/*.py."""


class QKeySequence:
    """Fake QKeySequence, string-backed.

    Real QKeySequence's Python constructor is sip-typed to accept a str
    (or an int/QKeySequence.StandardKey) -- passing something else (e.g.
    another arbitrary object) raises TypeError at the sip boundary. This
    fake enforces the same str-or-QKeySequence-only rule so a test that
    accidentally passes the wrong type fails the same way the real
    binding would, rather than silently accepting it.
    """

    def __init__(self, sequence=""):
        if isinstance(sequence, QKeySequence):
            self._seq = sequence._seq
        elif sequence is None:
            self._seq = ""
        elif isinstance(sequence, str):
            self._seq = sequence
        else:
            raise TypeError(
                f"QKeySequence(...): argument 1 has unexpected type '{type(sequence).__name__}'"
            )

    def toString(self) -> str:
        return self._seq

    def isEmpty(self) -> bool:
        return self._seq == ""

    def __eq__(self, other):
        if isinstance(other, QKeySequence):
            return self._seq == other._seq
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self._seq)

    def __repr__(self):
        return f"QKeySequence({self._seq!r})"


class QIcon:
    """Fake QIcon -- only isNull() is ever inspected by core/*.py."""

    def __init__(self, source=None):
        self._is_null = source is None

    def isNull(self) -> bool:
        return self._is_null
