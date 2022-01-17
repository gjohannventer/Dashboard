from flask import Flask, render_template, request
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Prometheus metrics
metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info('frontend_app_info', 'FrontEnd Application Info', version='1.0.1')
metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)
metric_endpoint_counter = metrics.counter(
    'endpoint_counter', 'Request count by endpoints',
    labels={'endpoint': lambda: request.endpoint}
)


@app.route("/")
@metric_endpoint_counter
def homepage():
    return render_template("main.html")

if __name__ == "__main__":
    app.run()
