import bokeh.embed
import bokeh.models
from bokeh.palettes import Dark2_5 as palette
import bokeh.plotting
import bokeh.resources
import itertools
from jinja2 import Environment, PackageLoader
import pandas

from .definitions import Engine, Report, Section, Box, Grid, Table, TextStyle, LineChart, ComboChart


class HtmlEngine(Engine):
    """
    HTML report rendering using jinja2 templates
    """
    def __init__(self, template='report.html'):
        self._env = None
        self._defaults = {
            'render': self._render
        }
        self._template = template
        self._include_js = True

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

        self._include_js = True
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
        box = self._env.get_template('box.html')
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
        fig = bokeh.plotting.figure(
            toolbar_location=None,
            tools="hover",
            title=obj.title,
            plot_width=500 if obj.size == LineChart.MEDIUM else 700,
            plot_height=350 if obj.size == LineChart.MEDIUM else 450,
        )

        colors = itertools.cycle(palette)

        for s in obj.series:
            fig.line(x=s.x, y=s.y, legend=s.title, color=next(colors))

        self._include_js = False
        return bokeh.embed.file_html(fig, bokeh.resources.CDN)

    def _render_combo_chart(self, obj):
        """
        Render a combination of lines and bars on the same chart.
        :param obj: ComboChart
        :return: HTML
        """
        fig = bokeh.plotting.figure(
            toolbar_location=None,
            tools="hover",
            title=obj.title,
            plot_width=500 if obj.size == LineChart.MEDIUM else 700,
            plot_height=350 if obj.size == LineChart.MEDIUM else 450,
        )

        colors = itertools.cycle(palette)

        # render bars:
        fig.extra_y_ranges['y2'] = bokeh.models.DataRange1d()
        fig.add_layout(bokeh.models.LinearAxis(y_range_name='y2'), 'right')
        bars = []
        for s in obj.bars:
            bars.append(fig.vbar(x=s.x, top=s.y, width=0.8, legend=s.title, y_range_name='y2',
                                 color=s.color if s.color is not None else next(colors)))
        fig.extra_y_ranges['y2'].renderers = bars

        # render lines
        for s in obj.lines:
            color = next(colors)
            # TODO: sort line values
            fig.line(x=s.x, y=s.y, legend=s.title, color=color)
            fig.circle(x=s.x, y=s.y, size=6, legend=s.title, fill_color='white', color=color)

        self._include_js = False
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
