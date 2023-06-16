import typing

class IncrementalEncoder:
    def encode(self, in_: str, final: bool) -> bytes: ...
    def reset(self) -> None: ...
    def getstate(self) -> int: ...
    def setstate(self, state: int) -> None: ...
    def __init__(self, encoding: str, conv_mode: int) -> None: ...

class TransliterationError(Exception): ...

def jnta_encode(encoding: str, in_: str, conv_mode: int) -> bytes: ...
def jnta_decode(encoding: str, in_: bytes) -> str: ...
def jnta_shrink_translit(
    in_: str, replacement: str = "\ufffe", passthrough: bool = False
) -> str: ...
def mj_shrink_candidates(
    in_: str, combo: int, limit: int = 100
) -> typing.List[str]: ...
