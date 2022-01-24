from flask import Flask, render_template, request, jsonify
import logging
from prometheus_flask_exporter import PrometheusMetrics


# Jaeger
from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory

# Tracing
from flask_opentracing import FlaskTracing
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

app = Flask(__name__)

# Instruments
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

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

# Initialize Jeager
def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        service_name=service,
        validate=True
    )

    # this call also sets opentracing.tracer
    return config.initialize_tracer()

tracer = init_tracer('frontend')
tracing = FlaskTracing(tracer, True, app)

@app.route("/")
@metric_endpoint_counter
def homepage():
    return render_template("main.html")

class InvalidRequest(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        print('I are here!')
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        payload_dictionary = dict(self.payload or ())
        payload_dictionary["message"] = self.message
        return payload_dictionary

@app.errorhandler(InvalidRequest)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/403")
def forbidden():
    status_code = 403
    raise InvalidRequest(
        "Raising status code: {}".format(status_code), status_code=status_code
    )

@app.route("/404")
def not_found():
    status_code = 404
    raise InvalidRequest(
        "Raising status code: {}".format(status_code), status_code=status_code
    )

@app.route("/500")
def internal_server_error():
    status_code = 500
    raise InvalidRequest(
        "Raising status code: {}".format(status_code), status_code=status_code
    )

@app.route("/503")
def service_unavailable():
    status_code = 503
    raise InvalidRequest(
        "Raising status code: {}".format(status_code), status_code=status_code
    )

if __name__ == "__main__":
    app.run()
