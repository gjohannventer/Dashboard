from flask import Flask, render_template, request, jsonify
from os import getenv
import logging

# Mongo
import pymongo
from flask_pymongo import PyMongo

# Jaeger
from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory

# Tracing
from flask_opentracing import FlaskTracing
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Prometheus
from prometheus_flask_exporter import PrometheusMetrics


app = Flask(__name__)

# Instruments
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()


# Mongo
app.config["MONGO_DBNAME"] = "example-mongodb"
app.config[
    "MONGO_URI"
] = "mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb"
mongo = PyMongo(app)

# Prometheus metrics
metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info('backend', 'backend Api Metrics', version='1.0.1')
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
JAEGER_HOST = getenv('JAEGER_HOST', 'localhost') # help jaeger instance in observabilty namespace to find app in default namespace

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
            'local_agent': {'reporting_host': JAEGER_HOST },
        },
        service_name=service,
        validate=True
    )

    return config.initialize_tracer()

tracer  = init_tracer('backend')
tracing = FlaskTracing(tracer, True, app)


@app.route("/")
@metric_endpoint_counter
def homepage():
    with tracer.start_span('home-page'):
        message = "Hello World"
        return message


@app.route("/api")
@metric_endpoint_counter
def my_api():
    with tracer.start_span('my-api'):
        answer = "something"
        return jsonify(repsonse=answer)


@app.route("/star", methods=["POST"])
@metric_endpoint_counter
def add_star():
    with tracer.start_span('add-star'):
        star = mongo.db.stars
        name = request.json["name"]
        distance = request.json["distance"]
        star_id = star.insert({"name": name, "distance": distance})
        new_star = star.find_one({"_id": star_id})
        output = {"name": new_star["name"], "distance": new_star["distance"]}
        return jsonify({"result": output})

# For error generation purposes: 40x and 50x
class InvalidRequest(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        payload_dictionary = dict(self.payload or ())
        payload_dictionary["message"] = self.message
        return payload_dictionary

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
