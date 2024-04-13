from unittest import TestCase

import pandas
from reports.html_engine import HtmlEngine
from reports import Report, Section, Table, LineChart, DataSeries, ChartGroup, CandlestickChart


class TestReports(TestCase):
    """
    Test reports package
    """

    def test_reports(self):
        """
        Test writing a report
        """
        report = Report(
            "Test Report",
            Section(
                "Section #1",
                Table(pandas.DataFrame([(1, 2), (3, 4)], columns=['A', 'B']))
            ),
            Section(
                "Section #2",
                Table(pandas.DataFrame([(1, 2), (3, 4)], columns=['A', 'B']), interactive=False)
            ),
            Section(
                "Section #3",
                LineChart("Kuku", DataSeries(x=[1, 2, 3], y=[10, 20, 30]))
            ),
            Section(
                "Section #4",
                ChartGroup(
                    CandlestickChart(
                        "",
                        pandas.DataFrame([
                            [1, 2, 0.5, 1.5],
                            [1.5, 2.5, 1.0, 2.0],
                            [2.0, 2.5, 1.0, 1.5]
                        ], columns=['open', 'high', 'low', 'close'])
                    ),
                    LineChart(
                        "Profit",
                        DataSeries(x=[0, 1, 2], y=[10, 20, 5])
                    )
                )
            )
        )

        html = HtmlEngine().render(report)
        with open('/tmp/kuku.html', 'w') as s:
            s.write(html)
