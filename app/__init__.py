from flask import Flask, send_file, request

app = Flask(__name__)


@app.route('/rows')
def get_rows():
    date = request.query_string.decode("utf-8")
    filename = "../results/rows-{}.json".format(date)
    return send_file(filename)


@app.route('/stops')
def get_stops():
    date = request.query_string.decode("utf-8")
    filename = "../results/stops-{}.json".format(date)
    return send_file(filename)


if __name__ == '__main__':
    app.run(debug=True)
