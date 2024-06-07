import dataclasses
from abc import abstractmethod
from typing import Sequence, Tuple, List

import pandas


class Engine:
    """
    Base engine definition
    """
    _engines_ = {}

    @abstractmethod
    def render(self, report):
        pass

    @staticmethod
    def get_engine(name: str) -> 'Engine':
        return Engine._engines_[name]()


@dataclasses.dataclass
class Content:
    """
    Base class for abstract content item.
    """
    pass


@dataclasses.dataclass
class Box(Content):
    """
    Content group. Can group content vertically / horizontally.
    """
    content: List[Content] = None
    orientation: str = "vertical"
    spacing: int = 0

    def __init__(self, *content, orientation: str = "vertical", spacing=0):
        super().__init__()
        self.content = list(content)
        self.orientation = orientation
        self.spacing = spacing


@dataclasses.dataclass
class Grid(Content):
    """
    Displays a grid
    """
    content: Sequence[Content] = None
    columns: int = 1

    def __init__(self, *content, columns=1):
        super().__init__()
        self.columns = columns
        self.content = list(content)


@dataclasses.dataclass
class Section(Box):
    """
    Report subsection definition
    """
    title: str = None
    level: int = 0

    def __init__(self, title, *content, orientation='vertical'):
        super().__init__(*content, orientation=orientation)
        self.title = title
        self.level = 0


@dataclasses.dataclass
class Report(Section):
    """
    Top-level report object for abstract report definition
    """
    def __init__(self, title, *content):
        super().__init__(title, *content)

    def update_levels(self):
        """
        Update section levels prior to rendering
        """
        todo = [(self, 0)]

        while len(todo):
            o, l = todo.pop()

            if isinstance(o, Section):
                o.level = l
                l += 1

            if isinstance(o, Box):
                todo += [(c, l) for c in o.content]

    def _repr_html_(self):
        """
        Jupyter integration
        """
        return Engine.get_engine('html').render(self)


@dataclasses.dataclass
class Table(Content):
    """
    Rendering for a table. Data should be pandas DataFrame

    :param data: pandas.DataFrame with data to render
    :param title: table title (optional)
    :param column_style: callback function to return styles per column
    :param interactive: if True, render interactive table (scrollable, selectable)
    """
    data: pandas.DataFrame = None
    title: str = None
    index: bool = False
    header: bool = True
    column_style: str = None
    interactive: bool = True


@dataclasses.dataclass(frozen=True, slots=True)
class TextStyle:
    """
    Text styling for tables. All values are in CSS units.
    """
    BOLD = 'bold'

    size: str = None
    weight: str = None
    align: str = None
    color: str = None


@dataclasses.dataclass(slots=True)
class DataSeries:
    """
    Single data series.

    :param title: data series name
    :param x: x values
    :param y: y values
    :param color: single color or color per point
    """
    title: str = None
    x: Sequence[float | str] = None
    y: Sequence[float] = None
    color: str = None
    line: bool = True
    markers: bool = False


@dataclasses.dataclass
class Annotation:
    """
    Base class for chart annotations
    """
    pass


@dataclasses.dataclass
class Chart(Content):
    """
    Base chart class
    """
    LARGE = 'large'  # chart size hints
    MEDIUM = 'medium'
    SMALL = 'small'
    WIDE = 'wide'
    AUTO = 'auto'  # size according to the container

    title: str = None
    series: Sequence[DataSeries] = None
    size: str | Tuple[int, int] = MEDIUM
    annotations: Sequence[Annotation] = None

    def __init__(self, title, *series, size=MEDIUM, annotations=None):
        super().__init__()
        self.title = title
        self.series = list(series)
        self.size = size
        self.annotations = annotations


@dataclasses.dataclass(slots=True)
class XYChart(Chart):
    """
    Base class for charts with X and Y axis
    """
    x_axis_title: str = None
    y_axis_title: str = None

    def __init__(self, title, *series, size=Chart.MEDIUM, x_axis_title=None, y_axis_title=None, annotations=None):
        super(XYChart, self).__init__(title, *series, size=size, annotations=annotations)
        self.x_axis_title = x_axis_title
        self.y_axis_title = y_axis_title


class LineChart(XYChart):
    """
    Simple line chart (scatter chart)
    """
    pass


@dataclasses.dataclass
class CandlestickChart(XYChart):
    """
    OHLC (open, high, low, close) chart
    """
    data: pandas.DataFrame = None

    def __init__(self, title: str, data: pandas.DataFrame, **kwargs):
        """
        Initialize with specified data

        :param title: chart title
        :param data: OHLC data
        """
        super().__init__(title, **kwargs)
        self.data = data


@dataclasses.dataclass(slots=True)
class ComboChart(XYChart):
    """
    Render a combined chart with bar and line series
    """
    bars: Sequence[DataSeries] = dataclasses.field(default_factory=list)
    lines: Sequence[DataSeries] = dataclasses.field(default_factory=list)

    def __init__(self, title, bars: Sequence[DataSeries], lines: Sequence[DataSeries], **kwargs):
        super(ComboChart, self).__init__(title, **kwargs)
        self.bars = bars
        self.lines = lines


class BarChart(XYChart):
    """
    Displays data series as bars
    """
    pass


@dataclasses.dataclass(slots=True)
class ChartGroup(Content):
    """
    Displays a grid of charts with shared X axis
    """
    charts: Sequence[XYChart] = dataclasses.field(default_factory=list)

    def __init__(self, *charts: XYChart):
        self.charts = list(charts)


class SlopeAnnotation(Annotation):
    """
    Slopes are rendered on the chart without affecting data ranges

    Renders line y(x) = slope * x + intercept
    """
    def __init__(self, intercept=0, slope=0, color=None, dash=None, line_width=None):
        super().__init__()
        self.intercept = intercept
        self.slope = slope
        self.intercept = intercept
        self.color = color
        self.dash = dash
        self.line_width = line_width
