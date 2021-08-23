import abc
import functools
import typing
from xml.parsers import expat


XMLDeclHandler = typing.Callable[[str, typing.Optional[str], int], None]
XMLStartDoctypeDeclHandler = typing.Callable[
    [str, typing.Optional[str], typing.Optional[str], bool], None
]
XMLEndDoctypeDeclHandler = typing.Callable[[], None]
XMLElementDeclHandler = typing.Callable[
    [str, typing.Tuple[int, int, typing.Optional[str], typing.Tuple[typing.Any, ...]]],
    None,
]
XMLAttlistDeclHandler = typing.Callable[
    [str, str, str, typing.Optional[str], bool], None
]
XMLStartElementHandler = typing.Callable[
    [str, typing.Union[typing.Dict[str, str], typing.Sequence[typing.Tuple[str, str]]]],
    None,
]
XMLEndElementHandler = typing.Callable[[str], None]
XMLProcessingInstructionHandler = typing.Callable[[str, str], None]
XMLCharacterDataHandler = typing.Callable[[str], None]
XMLUnparsedEntityDeclHandler = typing.Callable[
    [str, typing.Optional[str], str, typing.Optional[str], str], None
]
XMLEntityDeclHandler = typing.Callable[
    [
        str,
        bool,
        typing.Optional[str],
        typing.Optional[str],
        str,
        typing.Optional[str],
        typing.Optional[str],
    ],
    None,
]
XMLNotationDeclHandler = typing.Callable[
    [str, typing.Optional[str], str, typing.Optional[str]], None
]
XMLStartNamespaceDeclHandler = typing.Callable[[str, str], None]
XMLEndNamespaceDeclHandler = typing.Callable[[str], None]
XMLCommentHandler = typing.Callable[[str], None]
XMLStartCdataSectionHandler = typing.Callable[[], None]
XMLEndCdataSectionHandler = typing.Callable[[], None]
XMLDefaultHandler = typing.Callable[[str], None]
XMLDefaultHandlerExpand = typing.Callable[[str], None]
XMLNotStandaloneHandler = typing.Callable[[], bool]
XMLExternalEntityRefHandler = typing.Callable[
    [str, typing.Optional[str], typing.Optional[str], typing.Optional[str]], bool
]
EventPuller = typing.Callable[[], typing.Iterable[typing.Any]]


class XMLParserHandlers(typing.NamedTuple):
    xml_decl_handler: typing.Optional[XMLDeclHandler] = None
    start_doctype_decl_handler: typing.Optional[XMLStartDoctypeDeclHandler] = None
    end_doctype_decl_handler: typing.Optional[XMLEndDoctypeDeclHandler] = None
    element_decl_handler: typing.Optional[XMLElementDeclHandler] = None
    attlist_decl_handler: typing.Optional[XMLAttlistDeclHandler] = None
    start_element_handler: typing.Optional[XMLStartElementHandler] = None
    end_element_handler: typing.Optional[XMLEndElementHandler] = None
    processing_instruction_handler: typing.Optional[
        XMLProcessingInstructionHandler
    ] = None
    character_data_handler: typing.Optional[XMLCharacterDataHandler] = None
    unparsed_entity_decl_handler: typing.Optional[XMLUnparsedEntityDeclHandler] = None
    entity_decl_handler: typing.Optional[XMLEntityDeclHandler] = None
    notation_decl_handler: typing.Optional[XMLNotationDeclHandler] = None
    start_namespace_decl_handler: typing.Optional[XMLStartNamespaceDeclHandler] = None
    end_namespace_decl_handler: typing.Optional[XMLEndNamespaceDeclHandler] = None
    comment_handler: typing.Optional[XMLCommentHandler] = None
    start_cdata_section_handler: typing.Optional[XMLStartCdataSectionHandler] = None
    end_cdata_section_handler: typing.Optional[XMLEndCdataSectionHandler] = None
    default_handler: typing.Optional[XMLDefaultHandler] = None
    default_handler_expand: typing.Optional[XMLDefaultHandlerExpand] = None
    not_standalone_handler: typing.Optional[XMLNotStandaloneHandler] = None
    external_entity_ref_handler: typing.Optional[XMLExternalEntityRefHandler] = None
    pull_events: typing.Optional[EventPuller] = None


XMLParserHandlersFactory = typing.Callable[[expat.XMLParserType], XMLParserHandlers]


def create_parser(
    f: XMLParserHandlersFactory,
) -> typing.Tuple[expat.XMLParserType, typing.Optional[EventPuller]]:
    parser = expat.ParserCreate(namespace_separator="\n")

    handlers = f(parser)

    if handlers.xml_decl_handler is not None:
        parser.XmlDeclHandler = handlers.xml_decl_handler

    if handlers.start_doctype_decl_handler is not None:
        parser.StartDoctypeDeclHandler = handlers.start_doctype_decl_handler

    if handlers.end_doctype_decl_handler is not None:
        parser.EndDoctypeDeclHandler = handlers.end_doctype_decl_handler

    if handlers.element_decl_handler is not None:
        parser.ElementDeclHandler = handlers.element_decl_handler

    if handlers.attlist_decl_handler is not None:
        parser.AttlistDeclHandler = handlers.attlist_decl_handler

    if handlers.start_element_handler is not None:
        parser.StartElementHandler = handlers.start_element_handler

    if handlers.end_element_handler is not None:
        parser.EndElementHandler = handlers.end_element_handler

    if handlers.processing_instruction_handler is not None:
        parser.ProcessingInstructionHandler = handlers.processing_instruction_handler

    if handlers.character_data_handler is not None:
        parser.CharacterDataHandler = handlers.character_data_handler

    if handlers.unparsed_entity_decl_handler is not None:
        parser.UnparsedEntityDeclHandler = handlers.unparsed_entity_decl_handler

    if handlers.entity_decl_handler is not None:
        parser.EntityDeclHandler = handlers.entity_decl_handler

    if handlers.notation_decl_handler is not None:
        parser.NotationDeclHandler = handlers.notation_decl_handler

    if handlers.start_namespace_decl_handler is not None:
        parser.StartNamespaceDeclHandler = handlers.start_namespace_decl_handler

    if handlers.end_namespace_decl_handler is not None:
        parser.EndNamespaceDeclHandler = handlers.end_namespace_decl_handler

    if handlers.comment_handler is not None:
        parser.CommentHandler = handlers.comment_handler

    if handlers.start_cdata_section_handler is not None:
        parser.StartCdataSectionHandler = handlers.start_cdata_section_handler

    if handlers.end_cdata_section_handler is not None:
        parser.EndCdataSectionHandler = handlers.end_cdata_section_handler

    if handlers.default_handler is not None:
        parser.DefaultHandler = handlers.default_handler

    if handlers.default_handler_expand is not None:
        parser.DefaultHandlerExpand = handlers.default_handler_expand

    if handlers.not_standalone_handler is not None:
        parser.NotStandaloneHandler = handlers.not_standalone_handler

    if handlers.external_entity_ref_handler is not None:
        parser.ExternalEntityRefHandler = handlers.external_entity_ref_handler

    return parser, handlers.pull_events


def read_xml(
    s: typing.IO[bytes],
    f: XMLParserHandlersFactory,
):
    parser, _ = create_parser(f)
    while True:
        c = s.read(4096)
        if not c:
            break
        parser.Parse(c, False)
    parser.Parse("", True)


def read_xml_incremental(
    s: typing.IO[bytes],
    f: XMLParserHandlersFactory,
) -> typing.Iterator[typing.Any]:
    parser, event_puller = create_parser(f)
    if event_puller is None:
        raise ValueError("no event puller provided")
    while True:
        c = s.read(4096)
        if not c:
            break
        parser.Parse(c, False)
        yield from event_puller()
    parser.Parse("", True)


T1 = typing.TypeVar("T1")
T2 = typing.TypeVar("T2")


def wrap_start_element_handler(
    h: typing.Callable[[T1, str, str, typing.OrderedDict[str, str]], T2],
) -> typing.Callable[
    [
        T1,
        str,
        typing.Union[
            typing.Dict[str, str],
            typing.Sequence[typing.Tuple[str, str]],
        ],
    ],
    T2,
]:
    @functools.wraps(h)
    def _(
        self: T1,
        name: str,
        attlist: typing.Union[
            typing.Dict[str, str], typing.Sequence[typing.Tuple[str, str]]
        ],
    ) -> T2:
        ns, _, ln = name.partition("\n")
        if ln == "":
            ln = ns
            ns = ""
        return h(self, ns, ln, typing.OrderedDict[str, str](attlist))

    return _


class InvalidXMLDocumentError(Exception):
    path: typing.Tuple[str, ...]
    column: int
    line: int
    reason: str

    @property
    def message(self):
        return f"{self.reason} at line {self.line} column {self.column} (/{'/'.join(self.path)})"

    def __str__(self):
        return self.message

    def __init__(
        self, path: typing.Tuple[str, ...], column: int, line: int, reason: str
    ):
        super().__init__()
        self.path = path
        self.column = column
        self.line = line
        self.reason = reason


class Handlers(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def start_element(
        self,
        name: str,
        attlist: typing.Union[
            typing.Dict[str, str], typing.Sequence[typing.Tuple[str, str]]
        ],
    ) -> typing.Optional["Handlers"]:
        ...  # pragma: nocover

    @abc.abstractmethod
    def end_element(self, name: str) -> typing.Optional["Handlers"]:
        ...  # pragma: nocover

    @abc.abstractmethod
    def cdata(self, data: str) -> typing.Optional["Handlers"]:
        ...  # pragma: nocover


class HandlersBase(Handlers):
    outer: typing.Optional["HandlersBase"]
    parser: expat.XMLParserType
    path: typing.Tuple[str, ...]

    def raise_invalid_xml_document_error(self, reason: str) -> InvalidXMLDocumentError:
        return InvalidXMLDocumentError(
            self.path,
            self.parser.CurrentColumnNumber,
            self.parser.CurrentLineNumber,
            reason,
        )

    def raise_unexpected_element(
        self, expected: typing.Union[str, typing.Sequence[str]], actual: str
    ) -> InvalidXMLDocumentError:
        _expected: str
        if isinstance(expected, str):
            _expected = expected
        else:
            if len(expected) > 1:
                _expected = ", ".join(expected[:-1]) + ", or " + expected[-1]
            else:
                _expected = expected[0]
        return InvalidXMLDocumentError(
            self.path,
            self.parser.CurrentColumnNumber,
            self.parser.CurrentLineNumber,
            f"unexpected element found: expecting {_expected}, got {actual}",
        )

    def next(self, h: typing.Type["HandlersBase"], ln: str) -> "HandlersBase":
        return h(outer=self, ln=ln)

    def _post_init(self) -> None:
        pass

    def __init__(
        self,
        *,
        outer: typing.Optional["HandlersBase"] = None,
        parser: typing.Optional[expat.XMLParserType] = None,
        ln: typing.Optional[str] = None,
    ) -> None:
        self.outer = outer
        if outer is not None:
            self.parser = outer.parser
            assert ln is not None
            self.path = outer.path + (ln,)
        else:
            assert parser is not None
            self.parser = parser
            self.path = (ln,) if ln is not None else ()
        self._post_init()


class HandlerShim:
    _impl: Handlers

    def start_element(
        self,
        name: str,
        attlist: typing.Union[
            typing.Dict[str, str], typing.Sequence[typing.Tuple[str, str]]
        ],
    ) -> None:
        impl = self._impl.start_element(name, attlist)
        if impl is not None:
            self._impl = impl

    def end_element(self, name: str) -> None:
        impl = self._impl.end_element(name)
        if impl is not None:
            self._impl = impl

    def cdata(self, data: str) -> None:
        impl = self._impl.cdata(data)
        if impl is not None:
            self._impl = impl

    def __init__(self, impl: Handlers) -> None:
        self._impl = impl
