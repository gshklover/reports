import json
import os
import uuid
from typing import Tuple, Dict, Union

import bokeh.embed
import bokeh.models
import numpy
from bokeh.palettes import Category10_10 as palette
# from bokeh.transform import dodge
import bokeh.core.properties
import bokeh.plotting
import bokeh.resources
import itertools
from jinja2 import Environment, PackageLoader
import markupsafe
import numbers
import pandas

from .definitions import Engine, Report, Section, Box, Grid, Table, TextStyle, LineChart, ComboChart, BarChart, SlopeAnnotation, CandlestickChart, ChartGroup, Content, Chart, Text
# TODO: move the function definition into reports
from pyutils.bokehutils import bars, add_crosshair

# pre-defined chart sizes
CHART_SIZE = {
    LineChart.SMALL: (200, 200),
    LineChart.MEDIUM: (500, 350),
    LineChart.LARGE: (700, 450),
    LineChart.WIDE: (1000, 350)
}

DEFAULT_TOOLS = "pan,box_zoom,xwheel_zoom,reset,hover,crosshair"


class HtmlEngine(Engine):
    """
    HTML report rendering using jinja2 templates
    """
    def __init__(self, template='report.html', inline=True):
        self._env = None
        self._defaults = {
            'render': self._render,
            'is_inline': inline
        }
        self._template = template

    def render(self, report: Content) -> str:
        """
        Render report into HTML string

        :param report: Report object
        """
        self._env = Environment(
            loader=PackageLoader('reports', 'templates')
        )

        # update section levels
        if isinstance(report, Report):
            report.update_levels()
            template = self._env.get_template(self._template)
            return template.render(
                data=report, **self._defaults
            )

        # return self._render(report)
        # add styles:
        with open(os.path.join(os.path.dirname(__file__), 'templates', 'style.html')) as stream:
            styles = stream.read()
        return styles + '\n' + self._render(report)

    def _render(self, obj: Content) -> str:
        """
        Render a content object
        """
        obj_map = {
            Section: self._render_section,
            Box: self._render_box,
            Grid: self._render_grid,
            Table: self._render_table,
            Text: self._render_text,
            ChartGroup: self._render_chart_group
        }

        if isinstance(obj, Report):
            if obj.level == 0:
                return self._render_report(obj)
            else:
                return self._render_section(obj)

        if isinstance(obj, Chart):
            return self._render_chart(obj)

        if type(obj) not in obj_map:
            raise Exception("Unknown content type: " + str(type(obj)))

        return obj_map[type(obj)](obj)

    def _render_report(self, obj: Report) -> str:
        """
        Render top-level report object
        """
        if obj.level == 0:
            box = self._env.get_template('box.html')
        else:
            box = self._env.get_template('section.html')
        return box.render(data=obj, **self._defaults)

    def _render_section(self, obj: Section) -> str:
        """
        Render a subsection
        """
        box = self._env.get_template('section.html')
        return box.render(data=obj, **self._defaults)

    def _render_box(self, obj: Box) -> str:
        """
        Render a horizontal / vertical group of content
        """
        box = self._env.get_template('box.html')
        return box.render(data=obj, **self._defaults)

    def _render_grid(self, obj: Grid) -> str:
        """
        Render grid of objects
        """
        grid = self._env.get_template('grid.html')
        return grid.render(data=obj, **self._defaults)

    def _render_text(self, obj: Text) -> str:
        """
        Render text content
        """
        return f'<p>\n{str(markupsafe.escape(obj.text))}\n</p>' if obj.escape else obj.text

    def _render_interactive_table(self, obj: Table) -> str:
        """
        Render interactive table using jspreadsheets-ce package.
        """
        df = obj.data

        data = [list() for _ in range(df.shape[0])]
        columns = []

        for cname, dtype in zip(df.columns, df.dtypes):
            col = {'title': str(cname)}

            if pandas.api.types.is_datetime64_any_dtype(dtype):
                col['type'] = 'date'
                for i, val in enumerate(df[cname].values):
                    if pandas.isna(val):
                        data[i].append('')
                    else:
                        data[i].append(str(val))
            elif numpy.issubdtype(dtype, float):
                col['type'] = 'numeric'
                for i, val in enumerate(df[cname].values):
                    data[i].append(float(val))
            elif numpy.issubdtype(dtype, int):
                col['type'] = 'numeric'
                for i, val in enumerate(df[cname].values):
                    data[i].append(int(val))
            else:
                col['type'] = 'text'
                for i, val in enumerate(df[cname].values):
                    data[i].append(str(val))

            columns.append(col)

        div_id = str(uuid.uuid4())
        title = f'<div><b>{obj.title}</b></div>' if obj.title else ''

        return f'''
            <div>
            {title}
            <div id="{div_id}"></div>
            <script>
                var data = {json.dumps(data)};
                jspreadsheet(document.getElementById('{div_id}'), {{
                    data: data,
                    columns: {json.dumps(columns)},
                    editable: false,
                    columnResize: true,
                    columnDrag: false,
                    rowDrag: false
                }});
            </script>
            </div>
        '''

    def _render_html_table(self, obj: Table) -> str:
        """
        Render static HTML table
        """
        # NOTE: overrides default width=100% from bootstrap
        style = obj.data.style.set_table_attributes('class="table table-bordered table-sm table-responsive table-striped" style="width: initial;"')
        table_styles = []
        # if not obj.header:
        #     table_styles.append({'selector': '.col_heading', 'props': [('display', 'none')]})
        #
        # if not obj.index:
        #     table_styles.append({'selector': '.row_heading', 'props': [('display', 'none')]})
        #     table_styles.append({'selector': '.blank.level0', 'props': [('display', 'none')]})

        if len(table_styles):
            style = style.set_table_styles(table_styles)

        if not obj.header:
           style = style.hide(axis=1)
        if not obj.index:
           style = style.hide(axis=0)

        if obj.column_style:
            if callable(obj.column_style):
                style = style.apply(lambda x: self._apply_style(x, obj.column_style), axis=0)
            else:
                if not isinstance(obj.column_style, dict):
                    raise Exception("Column style should be a callback or a dictionary")
                d = obj.column_style
                style = style.apply(lambda x: self._apply_style(x, d.get(x.name, None)), axis=0)

        res = style.to_html()

        if obj.title:
            res = f'<div><p><b>{obj.title}</b></p>{res}</div>'

        return res

    def _render_table(self, obj: Table) -> str:
        """
        Render pandas table
        """
        if obj.interactive:
            return self._render_interactive_table(obj)
        else:
            return self._render_html_table(obj)

    @staticmethod
    def _chart_size(size: str | Tuple[int, int]) -> Dict[str, int]:
        """
        Convert size to width / height
        """
        return {
            'width': CHART_SIZE[size][0] if isinstance(size, str) else size[0],
            'height': CHART_SIZE[size][1] if isinstance(size, str) else size[1]
        }

    def _render_line_chart(self, obj: LineChart) -> bokeh.plotting.figure:
        """
        Render a line chart using bokeh

        :param obj: LineChart
        """
        # non-numeric X axis:
        extra = {}
        if len(obj.series) and len(obj.series[0].x) and not isinstance(obj.series[0].x[0], numbers.Number):
            x_range = set()
            for s in obj.series:
                x_range |= set(s.x)

            extra['x_range'] = bokeh.models.FactorRange(*sorted(x_range))

        fig = bokeh.plotting.figure(
            # toolbar_location=None,
            tools=DEFAULT_TOOLS,
            title=obj.title,
            **self._chart_size(obj.size),
            **extra
        )

        if obj.annotations:
            self._render_annotations(fig, obj.annotations)

        colors = itertools.cycle(palette)

        for s in obj.series:
            color = next(colors) if s.color is None else s.color
            extra = {'legend_label': s.title} if s.title else {}
            assert s.line or s.markers

            if s.line:
                fig.line(x=s.x, y=s.y, **extra, color=color)

            if s.markers:
                fig.scatter(x=s.x, y=s.y, color=color, **(extra if not s.line else {}))

        if obj.x_axis_title:
            fig.xaxis.axis_label = obj.x_axis_title
        if obj.y_axis_title:
            fig.yaxis.axis_label = obj.y_axis_title

        # disable legend if no series visible:
        if len(obj.series) <= 1 and len(fig.legend):
            fig.legend[0].visible = False
        elif any(s.title is not None for s in obj.series):
            # move to bottom right if going up:
            if len(obj.series) and len(obj.series[0].y) and obj.series[0].y[-1] > obj.series[0].y[0]:
                fig.legend.location = "bottom_right"

        return fig

    def _render_bar_chart(self, obj: BarChart) -> bokeh.plotting.figure:
        """
        Render a bar chart using bokeh

        :param obj: BarChart
        """
        data = pandas.DataFrame({
            's' + str(i): pandas.Series(s.y, index=[str(v) for v in s.x]) for i, s in enumerate(obj.series)
        })
        # TODO: add color handling through data (so that proper index is used)
        data.index.name = 'x'
        data = data.reset_index().fillna(0)
        source = bokeh.models.ColumnDataSource(data)

        fig = bokeh.plotting.figure(
            # toolbar_location=None,
            tools=DEFAULT_TOOLS,
            title=obj.title,
            x_range=data['x'].values,  # categorical values must be str()
            **self._chart_size(obj.size)
        )

        colors = itertools.cycle(palette)

        for idx, s in enumerate(obj.series):
            bars(fig, x='x', y='s' + str(idx), num_total=len(obj.series), this_index=idx,
                 source=source, legend_label=s.title,
                 color=s.color if s.color is not None else next(colors))
            # fig.vbar(x=dodge('x', - width/2 + idx * width, range=fig.x_range),
            #          top='s' + str(idx), source=source,
            #          legend_label=s.title, width=width * 0.9,
            #          color=s.color if s.color is not None else next(colors))

        # disable legend
        if len(obj.series) <= 1:
            fig.legend[0].visible = False

        return fig

    def _render_candlestick_chart(self, obj: CandlestickChart) -> bokeh.plotting.figure:
        """
        Render OHLC chart to the report

        :param obj:
        :return:
        """
        data = obj.data
        green = data['close'] >= data['open']
        colors = numpy.array(['#FF0000'] * len(data.index))
        colors[green] = '#00AA00'
        index = numpy.arange(len(data.index))

        fig = bokeh.plotting.figure(
            title=obj.title,
            tools=DEFAULT_TOOLS,
            **self._chart_size(obj.size),
        )

        width = 0.6
        fig.segment(index, data.high, index, data.low, color="black")
        source = bokeh.models.ColumnDataSource({
            'x': index,
            'width': [width] * index.shape[0],
            'top': numpy.maximum(data['open'].values, data['close'].values),
            'bottom': numpy.minimum(data['open'].values, data['close'].values),
            'color': colors,
            # for tooltip
            'time': list(map(str, data.index.values)),
            'open': data['open'].values,
            'high': data['high'].values,
            'low': data['low'].values,
            'close': data['close'].values
        })

        bars = fig.vbar(x='x', width='width', top='top', bottom='bottom', source=source,
                        fill_color='color', line_color="black")

        # modify hover tool:
        for t in fig.tools:
            if isinstance(t, bokeh.models.HoverTool):
                t.anchor = 'bottom_center'
                t.attachment = 'below'
                t.renderers = [bars]
                break

        # time axis formatter
        formatter = """
            var idx = Math.trunc(tick)
            if (idx < 0 || idx != tick || idx >= labels.length) return ""
            return labels[idx]
        """

        fig.xaxis.formatter = bokeh.models.CustomJSTickFormatter(code=formatter, args={
            'labels': [str(v) for v in data.index]
        })

        if 'volume' in data.columns and numpy.any(data['volume'].values):
            # Adding extra Y range seems to affect the default range calculation (implemented in DataRange1d)
            # We override the default Y range with explicit calculation.
            # This may affect the plot if extra rendering is performed later.
            # One way to fix this is to explicitly assign relevant subset of renderers to DataRange1d.
            default_top = data['high'].max()
            default_bot = data['low'].min()
            fig.y_range = bokeh.models.Range1d(1.05 * default_bot - 0.05 * default_top,
                                               1.05 * default_top - 0.05 * default_bot)

            volume = data['volume'].values
            fig.extra_y_ranges = {"volume": bokeh.models.Range1d(start=0, end=volume.max() * 5)}
            fig.add_layout(bokeh.models.LinearAxis(y_range_name="volume"), 'right')
            fig.vbar(x=index, width=0.8, bottom=numpy.zeros(len(index)), top=volume,
                     fill_color=colors, y_range_name='volume', alpha=0.5, level='underlay')

        return fig

    def _render_combo_chart(self, obj: ComboChart) -> str:
        """
        Render a combination of lines and bars on the same chart.
        The X axis is assumed to be categorical.

        :param obj: ComboChart
        :return: HTML
        """
        x_range = []
        for s in obj.lines + obj.bars:
            for v in s.x:
                v = str(v)
                if v not in x_range:
                    x_range.append(v)

        fig = bokeh.plotting.figure(
            # toolbar_location=None,
            tools=DEFAULT_TOOLS,
            title=obj.title,
            x_range=x_range,
            **self._chart_size(obj.size)
        )

        colors = itertools.cycle(palette)

        # render bars:
        fig.extra_y_ranges['y2'] = bokeh.models.DataRange1d()
        fig.add_layout(bokeh.models.LinearAxis(y_range_name='y2'), 'right')

        bars = []
        for s in obj.bars:
            bars.append(fig.vbar(x=[str(v) for v in s.x], top=s.y, width=0.8, legend_label=s.title, y_range_name='y2',
                                 color=s.color if s.color is not None else next(colors)))
        fig.extra_y_ranges['y2'].renderers = bars

        # render lines
        for s in obj.lines:
            color = next(colors)
            # TODO: sort line values
            fig.line(x=[str(v) for v in s.x], y=s.y, legend_label=s.title, color=color)
            fig.scatter(x=[str(v) for v in s.x], y=s.y, size=6, fill_color='white', color=color)

        # disable legend
        if len(obj.lines) <= 1 and len(obj.bars) <= 1:
            fig.legend[0].visible = False

        return fig

    def _render_chart(self, chart: Chart, as_string=True) -> Union[str, bokeh.plotting.figure]:
        """
        Render specified chart
        """
        renderers = {
            BarChart: self._render_bar_chart,
            LineChart: self._render_line_chart,
            ComboChart: self._render_combo_chart,
            CandlestickChart: self._render_candlestick_chart
        }
        if type(chart) not in renderers:
            raise Exception("Unknown chart type")

        fig = renderers[type(chart)](chart)

        if as_string:
            return bokeh.embed.file_html(fig, bokeh.resources.CDN)

        return fig

    def _render_chart_group(self, group: ChartGroup) -> str:
        """
        Renders a group of axis-aligned charts
        """
        charts = []

        for chart in group.charts:
            charts.append(self._render_chart(chart, as_string=False))

        for chart in charts[1:]:
            chart.x_range = charts[0].x_range

        add_crosshair(*charts)

        return bokeh.embed.file_html(bokeh.plotting.gridplot([[chart] for chart in charts]))

    def _apply_style(self, series, style):
        """
        Clone single style N times according to series shape
        :param series: pandas.Series() object
        :param style: TextStyle instance, None or callable
        :return: pandas.Series() with CSS style
        """
        if callable(style):
            style = style(series)

        if hasattr(style, '__len__'):
            style = [self._text_style_to_css(s) if s is not None else '' for s in style]
        else:
            style = self._text_style_to_css(style) if style is not None else ''
            style = [style] * len(series)
        return pandas.Series(style, index=series.index)

    def _text_style_to_css(self, text_style):
        """
        Convert TextStyle to CSS
        """
        if text_style is None:
            return ''

        result = []

        if text_style.weight == TextStyle.BOLD:
            result.append('font-weight: bold')

        if text_style.size:
            result.append('font-size: {}'.format(text_style.size))

        if text_style.color is not None:
            result.append('color: {}'.format(text_style.color))

        return '; '.join(result)

    def _render_annotations(self, figure, annotations):
        """
        Render annotation on the specified figure

        :param figure: bokeh.Figure
        :param annotations: list of chart annotations
        """
        for a in annotations:
            if isinstance(a, SlopeAnnotation):
                figure.add_layout(bokeh.models.Slope(
                    gradient=a.slope, y_intercept=a.intercept,
                    line_color=a.color or 'grey', line_dash=a.dash or [], line_width=a.line_width or 1
                ))
            else:
                raise NotImplementedError()


Engine._engines_['html'] = HtmlEngine


def save_report(report: Report, file: str):
    """
    Save report as HTML file

    :param report:
    :param file:
    :return:
    """
    eng = HtmlEngine()

    with open(file, 'w') as stream:
        stream.write(eng.render(report))

    return report
