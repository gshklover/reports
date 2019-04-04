class Engine:
    """
    Base engine definition
    """
    def render(self, report):
        pass


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
    def __init__(self, *content, orientation="vertical"):
        super().__init__()
        self._content = list(content)
        self._orient = orientation

    @property
    def content(self):
        return self._content

    @property
    def orientation(self):
        return self._orient


class Section(Box):
    """
    Report sub-section definition
    """
    def __init__(self, title, *content):
        super().__init__(*content)
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

    def __init__(self, size=None, weight=None, align=None):
        self._size = size
        self._weight = weight
        self._align = align

    @property
    def size(self):
        return self._size

    @property
    def weight(self):
        return self._weight

    @property
    def align(self):
        return self._align


class Chart(Content):
    """
    Base chart class
    """
    LARGE = 'large'  # chart size hints
    MEDIUM = 'medium'
    SMALL = 'small'
    AUTO = 'auto'  # size according to the container

    def __init__(self, title=None, *series, size=MEDIUM):
        self._title = title
        self._series = list(series)
        self._size = size

    @property
    def title(self):
        return self._title

    @property
    def series(self):
        return self._series

    @property
    def size(self):
        return self._size


class LineChart(Chart):
    """
    Simple line chart
    """
    def __init__(self, title, *series, size=Chart.MEDIUM):
        super().__init__(title, *series, size=size)


class ComboChart(Chart):
    """
    Render a combined chart with bar and line series
    """
    def __init__(self, title, bars=[], lines=[], size=Chart.MEDIUM):
        super().__init__(title, size=size)
        self.bars = bars
        self.lines = lines


class DataSeries:
    """
    Single data series.
    """
    def __init__(self, title=None, x=None, y=None):
        self._title = title
        self._x = x
        self._y = y

    @property
    def title(self):
        return self._title

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y


class CandlestickChart(Chart):
    """
    Candlestick chart for rendering OHLC data
    """
    def __init__(self, title, series):
        super().__init__(title)
