from unittest import TestCase

import pandas
from reports.html_engine import HtmlEngine
from reports.definitions import Report, Section, Table, LineChart, DataSeries


class TestReports(TestCase):
    def test_reports(self):
        report = Report("Test Report",
                        Section("Section #1", Table(pandas.DataFrame([(1, 2), (3, 4)], columns=['A', 'B']))),
                        Section("Section #2", LineChart("Kuku", DataSeries(x=[1, 2, 3], y=[10, 20, 30])))
                        )

        html = HtmlEngine().render(report)
        with open('/tmp/kuku.html', 'w') as s:
            s.write(html)
