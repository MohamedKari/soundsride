import dash_core_components as dcc
import dash_html_components as html

class DashMixPlan:

    def get_component(self) -> html.Div:
        return html.Div([
            dcc.Graph(id="graph-mix-plan")
        ])