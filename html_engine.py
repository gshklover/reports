import bokeh.embed
import bokeh.models
from bokeh.palettes import Category10_10 as palette
# from bokeh.transform import dodge
import bokeh.core.properties
import bokeh.plotting
import bokeh.resources
import itertools
from jinja2 import Environment, PackageLoader
import numbers
import pandas

from .definitions import Engine, Report, Section, Box, Grid, Table, TextStyle, LineChart, ComboChart, BarChart, SlopeAnnotation
# TODO: move the function definition into reports
from pyutils.bokehutils import bars


CHART_SIZE = {
    LineChart.SMALL: (200, 200),
    LineChart.MEDIUM: (500, 350),
    LineChart.LARGE: (700, 450),
    LineChart.WIDE: (1000, 350)
}


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

    def render(self, report):
        """
        Render report into HTML string
        :param report: Report object
        """
        self._env = Environment(
            loader=PackageLoader('reports', 'templates'))

        # update section levels
        report.update_levels()
        template = self._env.get_template(self._template)

        return template.render(
            data=report, **self._defaults
        )

    def _render(self, obj):
        """
        Render a content object
        """
        obj_map = {
            Report: self._render_report,
            Section: self._render_section,
            Box: self._render_box,
            Grid: self._render_grid,
            Table: self._render_table,
            BarChart: self._render_bar_chart,
            LineChart: self._render_line_chart,
            ComboChart: self._render_combo_chart,
        }

        if type(obj) not in obj_map:
            raise(Exception("Unknown content type: " + str(type(obj))))

        return obj_map[type(obj)](obj)

    def _render_report(self, obj):
        """
        Render top-level report object
        """
        if obj.level == 0:
            box = self._env.get_template('box.html')
        else:
            box = self._env.get_template('section.html')
        return box.render(data=obj, **self._defaults)

    def _render_section(self, obj):
        """
        Render a sub-section
        """
        box = self._env.get_template('section.html')
        return box.render(data=obj, **self._defaults)

    def _render_box(self, obj):
        """
        Render a horizontal / vertical group of content
        """
        box = self._env.get_template('box.html')
        return box.render(data=obj, **self._defaults)

    def _render_grid(self, obj):
        """
        Render grid of objects
        """
        grid = self._env.get_template('grid.html')
        return grid.render(data=obj, **self._defaults)

    def _render_table(self, obj):
        """
        Render pandas table
        """
        style = obj.data.style.set_table_attributes('class="table-sm table-striped"')
        table_styles = []
        if not obj.header:
            table_styles.append({'selector': '.col_heading', 'props': [('display', 'none')]})

        if not obj.index:
            table_styles.append({'selector': '.row_heading', 'props': [('display', 'none')]})
            table_styles.append({'selector': '.blank.level0', 'props': [('display', 'none')]})

        if len(table_styles):
            style = style.set_table_styles(table_styles)

        # not supported yet, available in v0.23
        # if not obj.header:
        #    style = style.hide_header()
        # if not obj.index:
        #    style = style.hide_index()

        if obj.column_style:
            if callable(obj.column_style):
                style = style.apply(lambda x: self._apply_style(x, obj.column_style), axis=0)
            else:
                if not isinstance(obj.column_style, dict):
                    raise(Exception("Column style should be a callback or a dictionary"))
                d = obj.column_style
                style = style.apply(lambda x: self._apply_style(x, d.get(x.name, None)), axis=0)

        return style.render()

    def _render_line_chart(self, obj):
        """
        Render a line chart using bokeh

        :param obj: LineChart
        """
        # non-numeric X axis:
        if len(obj.series) and len(obj.series[0].x) and not isinstance(obj.series[0].x[0], numbers.Number):
            x_range = set()
            for s in obj.series:
                x_range |= set(s.x)

            x_range = bokeh.models.FactorRange(*sorted(x_range))
        else:
            x_range = None

        fig = bokeh.plotting.figure(
            # toolbar_location=None,
            # tools="hover",
            title=obj.title,
            plot_width=CHART_SIZE[obj.size][0],
            plot_height=CHART_SIZE[obj.size][1],
            x_range=x_range
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
                fig.circle(x=s.x, y=s.y, color=color)

        if obj.x_axis_title:
            fig.xaxis.axis_label = obj.x_axis_title
        if obj.y_axis_title:
            fig.yaxis.axis_label = obj.y_axis_title

        # disable legend
        if len(obj.series) <= 1 and len(fig.legend):
            fig.legend[0].visible = False
        else:
            if len(obj.series) and len(obj.series[0].y) and obj.series[0].y[-1] > obj.series[0].y[0]:
                fig.legend.location = "bottom_right"

        return bokeh.embed.file_html(fig, bokeh.resources.CDN)

    def _render_bar_chart(self, obj):
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
            # tools="hover",
            title=obj.title,
            x_range=data['x'].values,  # categorical values must be str()
            plot_width=CHART_SIZE[obj.size][0],
            plot_height=CHART_SIZE[obj.size][1],
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

        return bokeh.embed.file_html(fig, bokeh.resources.CDN)

    def _render_combo_chart(self, obj):
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
            # tools="hover",
            title=obj.title,
            x_range=x_range,
            plot_width=CHART_SIZE[obj.size][0],
            plot_height=CHART_SIZE[obj.size][1],
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
            fig.circle(x=[str(v) for v in s.x], y=s.y, size=6, fill_color='white', color=color)

        # disable legend
        if len(obj.lines) <= 1 and len(obj.bars) <= 1:
            fig.legend[0].visible = False

        return bokeh.embed.file_html(fig, bokeh.resources.CDN)

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


def save_report(report, file):
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
