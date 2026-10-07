import os

from flask import Flask, request
import numpy as np

MODEL_PATH = env_var = os.environ["MODEL_PATH"]

app = Flask(__name__)


@app.route("/")
def model_documentation():
    return """
<h1>Welcome to customer spent prediction model</h1>

<p>Please use our api to use the model:</p>
<p>curl localhost:8000/model?minutes=5</p>
"""


@app.route("/model")
def model():
    minutes = request.args.get('minutes')
    model = np.poly1d(np.load(MODEL_PATH))
    return {"spent": model(int(minutes))}
