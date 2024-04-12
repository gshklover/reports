import pandas


class Engine:
    """
    Base engine definition
    """
    _engines_ = {}

    def render(self, report):
        pass

    @staticmethod
    def get_engine(name):
        return Engine._engines_[name]()


class Content:
    """
    Base class for abstract content item.
    """
    def __init__(self):
        pass


class Box(Content):
    """
    Content group. Can group content vertically / horizontally.
    """
    def __init__(self, *content, orientation="vertical", spacing=0):
        super().__init__()
        self._content = list(content)
        self._orient = orientation
        self._spacing = spacing

    @property
    def content(self):
        return self._content

    @property
    def orientation(self):
        return self._orient


class Grid(Content):
    """
    Displays a grid
    """
    def __init__(self, *content, columns=1):
        super().__init__()
        self._columns = columns
        self._content = list(content)

    @property
    def content(self):
        return self._content

    @property
    def columns(self):
        return self._columns


class Section(Box):
    """
    Report sub-section definition
    """
    def __init__(self, title, *content, orientation='vertical'):
        super().__init__(*content, orientation=orientation)
        self._title = title
        self._level = 0

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, val):
        self._title = val

    @property
    def level(self):
        """
        Used internally when rendering
        """
        return self._level

    @level.setter
    def level(self, val):
        self._level = val


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


class Table(Content):
    """
    Rendering for a table. Data should be pandas DataFrame
    :param data: pandas.DataFrame with data to render
    :param title: table title (optional)
    :param column_style: callback function to return styles per column
    """
    def __init__(self, data, title=None, index=False, header=True, column_style=None):
        super().__init__()
        self._data = data
        self._title = title
        self._index = index
        self._header = header
        self._column_style = column_style

    @property
    def data(self):
        return self._data

    @property
    def title(self):
        return self._title

    @property
    def index(self):
        return self._index

    @property
    def header(self):
        return self._header

    @property
    def column_style(self):
        return self._column_style


class TextStyle:
    """
    Text styling for tables. All values are in CSS units.
    """
    BOLD = 'bold'

    def __init__(self, size=None, weight=None, align=None, color=None):
        self._size = size
        self._weight = weight
        self._align = align
        self._color = color

    @property
    def size(self):
        return self._size

    @property
    def weight(self):
        return self._weight

    @property
    def align(self):
        return self._align

    @property
    def color(self):
        return self._color


class Chart(Content):
    """
    Base chart class
    """
    LARGE = 'large'  # chart size hints
    MEDIUM = 'medium'
    SMALL = 'small'
    WIDE = 'wide'
    AUTO = 'auto'  # size according to the container

    def __init__(self, title=None, *series, size=MEDIUM, x_axis_title=None, y_axis_title=None, annotations=None):
        super().__init__()
        self.title = title
        self.series = list(series)
        self.size = size
        self.x_axis_title = x_axis_title
        self.y_axis_title = y_axis_title
        self.annotations = annotations


class LineChart(Chart):
    """
    Simple line chart (scatter chart)
    """
    def __init__(self, title, *series, size=Chart.MEDIUM, x_axis_title=None, y_axis_title=None, annotations=None):
        super().__init__(title, *series, size=size, x_axis_title=x_axis_title, y_axis_title=y_axis_title,
                         annotations=annotations)


class OHLCChart(Chart):
    """
    OHLC (financial data) chart
    """
    def __init__(self, title, data: pandas.DataFrame, **kwargs):
        """

        :param title:
        :param data:
        """
        super().__init__(title=title, **kwargs)
        self.data = data


class ComboChart(Chart):
    """
    Render a combined chart with bar and line series
    """
    def __init__(self, title, bars=[], lines=[], size=Chart.MEDIUM):
        super().__init__(title, size=size)
        self.bars = bars
        self.lines = lines


class BarChart(Chart):
    """
    Displays data series as bars
    """
    def __init__(self, title, *series, size=Chart.MEDIUM):
        super().__init__(title, *series, size=size)


class DataSeries:
    """
    Single data series.

    :param title: data series name
    :param x: x values
    :param y: y values
    :param color: single color or color per point
    """
    def __init__(self, title=None, x=None, y=None, color=None, line=True, markers=False):
        self._title = title
        self._x = x
        self._y = y
        self._color = color
        self.line = line
        self.markers = markers

    @property
    def title(self):
        return self._title

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def color(self):
        return self._color


class CandlestickChart(Chart):
    """
    Candlestick chart for rendering OHLC data
    """
    def __init__(self, title, series):
        super().__init__(title)


class Annotation:
    """
    Base class for chart annotations
    """
    pass


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
