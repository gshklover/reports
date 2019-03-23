# reports
Python package for dynamically generating reports.

The main feature is separation between the front-end (report definition) and the backend (rendering).
The front-end provides classes for declaring abstract report structure: Report, Section, Table, Chart and some formatting hints (Box, TextStyle, ...).
The backends are responsible for rendering the report to a given file format.
Current implementation supports HTML rendering using jinja2 and plotly.

**Example:**
```python
report = Report("My Report Name",
                Section("Section #1",
                        Table(data=pandas.DataFrame(...)),
                        LineChart("Chart name", DataSeries(title="line #1", x=..., y=...))))
eng = HtmlEngine()
html = eng.render(report)
```

### API Reference ###
