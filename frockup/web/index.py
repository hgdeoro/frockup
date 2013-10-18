from flask import Flask, jsonify, request, json

app = Flask(__name__)
app.debug = True


@app.route('/')
def index():
    return jsonify({'ok': True})


@app.route('/callMethod/', methods=['GET', 'POST'])
def callMethod():
    # functionName : methodName,
    # functionArgs : functionArgs
    data = json.loads(request.data)
    data['functionName']
    data['functionArgs']
    import time
    time.sleep(1)
    return jsonify({'ok': True, 'directories': ('/', '/tmp', '/home')})


if __name__ == '__main__':
    app.run()
