from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def root():
    return render_template("index.html")


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Flask!"}
