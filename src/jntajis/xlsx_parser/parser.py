import dataclasses
import re
import types
import typing
import zipfile
from xml.parsers import expat

from .xmlutils import (
    Handlers,
    HandlersBase,
    HandlerShim,
    XMLParserHandlers,
    read_xml,
    read_xml_incremental,
    wrap_start_element_handler,
)

OPENXML_STRICT_NAMESPACE = "http://purl.oclc.org/ooxml/spreadsheetml/main"
OPENXML_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

possible_namespaces = {OPENXML_STRICT_NAMESPACE, OPENXML_NAMESPACE}


SharedStringsReaderContext = typing.List[str]


class SharedStringsReader(typing.Protocol):
    ctx: SharedStringsReaderContext


class SharedStringsReader_2(HandlersBase):
    c: int
    ctx: SharedStringsReaderContext
    expecting_value: bool = False
    _value: str = ""

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if self.c == 0:
            if ns not in possible_namespaces or ln not in ("t", "phoneticPr", "rPh"):
                self.raise_unexpected_element(("t", "phoneticPr", "rPh"), ln)
            if ln == "t":
                self.expecting_value = True
        self.c += 1
        return None

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        self.c -= 1
        self.expecting_value = False
        if self.c < 0:
            self.ctx.append(self._value)
            return self.outer
        else:
            return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        if self.expecting_value:
            self._value += data
        return None

    def _post_init(self) -> None:
        self.c = 0
        self.ctx = typing.cast(SharedStringsReader, self.outer).ctx


class SharedStringsReader_1(HandlersBase):
    c: int
    ctx: SharedStringsReaderContext

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if self.c == 0 and ns in possible_namespaces and ln == "si":
            return self.next(SharedStringsReader_2, ln)
        self.c += 1
        return None

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        self.c -= 1
        if self.c < 0:
            return self.outer
        else:
            return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        return None

    def _post_init(self) -> None:
        self.c = 0
        self.ctx = typing.cast(SharedStringsReader, self.outer).ctx


class SharedStringsReader_0(HandlersBase):
    ctx: SharedStringsReaderContext

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if ns not in possible_namespaces or ln != "sst":
            raise self.raise_unexpected_element("sst", ln)
        return self.next(SharedStringsReader_1, ln)

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        return None

    def __init__(self, *, ctx: SharedStringsReaderContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx


def build_shared_strings_path(z: zipfile.ZipFile) -> str:
    return "xl/sharedStrings.xml"


def read_shared_strings(z: zipfile.ZipFile) -> typing.Sequence[str]:
    ctx: SharedStringsReaderContext = []

    def build_handlers(parser: expat.XMLParserType) -> XMLParserHandlers:
        h = HandlerShim(SharedStringsReader_0(parser=parser, ctx=ctx))
        return XMLParserHandlers(
            start_element_handler=h.start_element,
            end_element_handler=h.end_element,
            character_data_handler=h.cdata,
        )

    with z.open(build_shared_strings_path(z), "r") as f:
        read_xml(f, build_handlers)

    return ctx


@dataclasses.dataclass
class OpenXMLFormula:
    value: str
    t: str
    ref: str
    si: str


@dataclasses.dataclass
class OpenXMLCell:
    value: typing.Union[OpenXMLFormula, str]
    r: str
    s: str
    t: typing.Optional[str] = None


@dataclasses.dataclass
class OpenXMLRow:
    cells: typing.Sequence[OpenXMLCell]
    r: str
    spans: typing.Optional[str] = None
    ht: typing.Optional[str] = None
    s: typing.Optional[str] = None
    customFormat: typing.Optional[str] = None
    customHeight: typing.Optional[str] = None
    thickBot: typing.Optional[str] = None
    thickTop: typing.Optional[str] = None


@dataclasses.dataclass
class WorksheetReaderHandlers:
    handle_dimension: typing.Callable[[str], None]
    handle_row: typing.Callable[[OpenXMLRow], None]


@dataclasses.dataclass
class IncrementalWorksheetReaderHandlers(WorksheetReaderHandlers):
    yield_rows: typing.Callable[[], typing.Iterator[typing.Any]]


WorksheetReaderContext = WorksheetReaderHandlers


class WorksheetReader(typing.Protocol):
    ctx: WorksheetReaderContext


class WorksheetReader_4(HandlersBase):
    c: int
    outer: "WorksheetReader_3"
    _elem_type: typing.Optional[str] = None
    _attlist: typing.Optional[typing.Dict[str, str]] = None
    _value: str = ""

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if self.c == 0:
            if ns not in possible_namespaces or ln not in ("v", "f"):
                self.raise_unexpected_element(("v", "f"), ln)
            self._elem_type = ln
            self._attlist = attlist
        self.c += 1
        return None

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        self.c -= 1
        if self.c < 0:
            if self._attlist is not None:
                value: typing.Union[str, OpenXMLFormula]
                self.outer.set_value(
                    OpenXMLFormula(value=self._value, **self._attlist)
                    if self._elem_type == "f"
                    else self._value
                )
            return self.outer
        else:
            return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        if self.c == 1 and self._elem_type is not None:
            self._value += data
        return None

    def _post_init(self) -> None:
        self.c = 0


class WorksheetReader_3(HandlersBase):
    c: int
    ctx: WorksheetReaderContext
    _attlist: typing.Optional[typing.Dict[str, str]] = None
    _cells: typing.List[OpenXMLCell]

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if self.c == 0:
            if ns not in possible_namespaces or ln != "c":
                self.raise_unexpected_element("c", ln)
            self._attlist = attlist
            return self.next(WorksheetReader_4, ln)
        self.c += 1
        return None

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        self.c -= 1
        if self.c < 0:
            assert self.outer is not None
            typing.cast("WorksheetReader_2", self.outer).set_cells(self._cells)
            return self.outer
        else:
            return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        return None

    def set_value(self, value: typing.Union[OpenXMLFormula, str]) -> None:
        assert self._attlist is not None
        self._cells.append(
            OpenXMLCell(
                value=value,
                **self._attlist,
            )
        )

    def _post_init(self) -> None:
        self.c = 0
        self.ctx = typing.cast(WorksheetReader, self.outer).ctx
        self._cells = []


class WorksheetReader_2(HandlersBase):
    c: int
    ctx: WorksheetReaderContext
    _attlist: typing.Optional[typing.Dict[str, str]] = None

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if self.c == 0:
            if ns not in possible_namespaces or ln != "row":
                self.raise_unexpected_element("row", ln)
            self._attlist = attlist
            return self.next(WorksheetReader_3, ln)
        self.c += 1
        return None

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        self.c -= 1
        if self.c < 0:
            return self.outer
        else:
            return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        return None

    def set_cells(self, cells: typing.List[OpenXMLCell]) -> None:
        assert self._attlist is not None
        self.ctx.handle_row(
            OpenXMLRow(
                cells=cells,
                **{k: v for k, v in self._attlist.items() if ":" not in k},
            ),
        )

    def _post_init(self) -> None:
        self.c = 0
        self.ctx = typing.cast(WorksheetReader, self.outer).ctx


class WorksheetReader_1(HandlersBase):
    c: int
    ctx: WorksheetReaderContext
    expecting_value: bool = False

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if self.c == 0:
            if ns in possible_namespaces:
                if ln == "dimension":
                    self.ctx.handle_dimension(attlist["ref"])
                elif ln == "sheetData":
                    return self.next(WorksheetReader_2, ln)
        self.c += 1
        return None

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        self.c -= 1
        if self.c < 0:
            return self.outer
        else:
            return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        return None

    def _post_init(self) -> None:
        self.c = 0
        self.ctx = typing.cast(WorksheetReader, self.outer).ctx


class WorksheetReader_0(HandlersBase):
    ctx: WorksheetReaderContext

    @wrap_start_element_handler
    def start_element(
        self,
        ns: str,
        ln: str,
        attlist: typing.OrderedDict[str, str],
    ) -> typing.Optional[Handlers]:
        if ns not in possible_namespaces or ln != "worksheet":
            raise self.raise_unexpected_element("worksheet", ln)
        return self.next(WorksheetReader_1, ln)

    def end_element(self, name: str) -> typing.Optional[Handlers]:
        return None

    def cdata(self, data: str) -> typing.Optional[Handlers]:
        return None

    def __init__(self, *, ctx: WorksheetReaderContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx


def build_worksheet_path(z: zipfile.ZipFile, i: int) -> str:
    return f"xl/worksheets/sheet{i}.xml"


def read_worksheet_incremental(
    z: zipfile.ZipFile, i: int, handlers: IncrementalWorksheetReaderHandlers
) -> typing.Iterator[typing.Any]:
    def build_handlers(parser: expat.XMLParserType) -> XMLParserHandlers:
        h = HandlerShim(WorksheetReader_0(parser=parser, ctx=handlers))
        return XMLParserHandlers(
            start_element_handler=h.start_element,
            end_element_handler=h.end_element,
            character_data_handler=h.cdata,
            pull_events=handlers.yield_rows,
        )

    with z.open(build_worksheet_path(z, i), "r") as f:
        yield from read_xml_incremental(f, build_handlers)


def parse_generic_span_str(v: str) -> typing.Tuple[str, str]:
    ss, d, es = v.partition(":")
    if not d:
        raise ValueError(f"invalid span string: {v}")
    return ss, es


def parse_row_span_str(v: str) -> typing.Tuple[int, int]:
    ss, ee = parse_generic_span_str(v)
    s: int
    e: int
    try:
        s = int(ss)
        e = int(ee)
    except ValueError:
        raise ValueError(f"invalid span string: {v}")
    return (s, e)


cell_ref_re = re.compile(r"([A-Za-z]+)([0-9]+)")


def parse_base26(digits: str) -> int:
    v = 0
    for dc in digits:
        d = ord(dc)
        if d < 0x41 or d > 0x5A:
            raise ValueError(f"invalid digit: {dc}")
        v = v * 26 + (d - 0x40)
    return v


def parse_cell_ref(v: str) -> typing.Tuple[int, int]:
    m = cell_ref_re.match(v)
    if m is None:
        raise ValueError(f"invalid cell reference: {v}")
    r = int(m.group(2))
    if r < 1:
        raise ValueError(f"invalid cell reference: {v}")
    return (parse_base26(m.group(1).upper()), r)


CellRef = typing.Tuple[int, int]


PlainRow = typing.Sequence[typing.Optional[str]]


class StreamingWorksheetReader:
    dimension: typing.Optional[typing.Tuple[CellRef, CellRef]] = None
    shared_strings: typing.Sequence[str]

    def handle_dimension(self, ref: str):
        lt, rb = parse_generic_span_str(ref)
        self.dimension = (parse_cell_ref(lt), parse_cell_ref(rb))

    def _extract_value_for_cell(self, c: OpenXMLCell) -> str:
        v: str
        if isinstance(c.value, str):
            if c.t == "s":
                v = self.shared_strings[int(c.value)]
            else:
                v = c.value
        else:
            assert isinstance(c.value, OpenXMLFormula)
            v = c.value.value
        return v

    def handle_row(self, row: OpenXMLRow):
        values: typing.List[typing.Optional[str]] = []
        span: typing.Optional[typing.Tuple[int, int]] = None
        num_cols: typing.Optional[int] = None
        if row.spans is not None:
            span = parse_row_span_str(row.spans)
            num_cols = span[1]
        if self.dimension is not None:
            dc = self.dimension[1][0]
            num_cols = dc if num_cols is None else max(dc, num_cols)
        s = 1
        for c in row.cells:
            cn, rn = parse_cell_ref(c.r)
            v = self._extract_value_for_cell(c)
            while s < cn:
                values.append(None)
                s += 1
            values.append(v)
            s += 1
        if num_cols is not None:
            while s <= num_cols:
                values.append(None)
                s += 1
        self.row_handler(values)

    def __init__(
        self,
        shared_strings: typing.Sequence[str],
        row_handler: typing.Callable[[PlainRow], None],
    ) -> None:
        self.shared_strings = shared_strings
        self.row_handler = row_handler


class ReadonlyWorksheet:
    wb: "ReadonlyWorkbook"
    i: int

    def iter_rows(self) -> typing.Iterator[PlainRow]:
        row_buffer = []

        def handle_row(row: PlainRow) -> None:
            row_buffer.append(row)

        def yield_rows() -> typing.Iterator[PlainRow]:
            nonlocal row_buffer
            retval = iter(row_buffer)
            row_buffer = []
            return retval

        r = StreamingWorksheetReader(
            self.wb._get_shared_strings(),
            handle_row,
        )
        return typing.cast(
            typing.Iterator[PlainRow],
            read_worksheet_incremental(
                z=self.wb.z,
                i=self.i,
                handlers=IncrementalWorksheetReaderHandlers(
                    handle_dimension=r.handle_dimension,
                    handle_row=r.handle_row,
                    yield_rows=yield_rows,
                ),
            ),
        )

    def __init__(self, wb: "ReadonlyWorkbook", i: int) -> None:
        self.wb = wb
        self.i = i


class ReadonlyWorkbook:
    z: zipfile.ZipFile
    _shared_strings: typing.Optional[typing.Sequence[str]] = None

    def _get_shared_strings(self) -> typing.Sequence[str]:
        if self._shared_strings is None:
            self._shared_strings = read_shared_strings(self.z)
        return self._shared_strings

    def get_worksheet_by_index(self, i: int) -> ReadonlyWorksheet:
        if i < 1:
            raise IndexError(f"index out of range: {i}")
        return ReadonlyWorksheet(self, i)

    def close(self):
        if self.z is not None:
            self.z.close()
            self.z = None

    def __enter__(self) -> "ReadonlyWorkbook":
        return self

    def __exit__(
        self,
        ext_type: typing.Type[BaseException],
        exc_value: BaseException,
        traceback: types.TracebackType,
    ) -> typing.Optional[bool]:
        self.close()
        return None

    def __del__(self):
        self.close()

    def __init__(self, z: zipfile.ZipFile) -> None:
        self.z = z


def read_xlsx(f: str) -> ReadonlyWorkbook:
    return ReadonlyWorkbook(zipfile.ZipFile(f, "r"))
