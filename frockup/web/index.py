from flask import Flask, jsonify, request, json
import traceback
import logging
import os

app = Flask(__name__)
app.debug = True


class Remote(object):

    def load_directory(self, function_args):
        base_dir = function_args[0]
        assert os.path.exists(base_dir)

        return {'directories': [x[0] for x in os.walk(base_dir)]}


remote = Remote()


@app.route('/')
def index():
    return jsonify({'ok': True})


@app.route('/callMethod/', methods=['GET', 'POST'])
def callMethod():
    data = json.loads(request.data)

    if not 'functionName' in data:
        raise(Exception("Parameter 'functionName' not found"))
    if not 'functionArgs' in data:
        raise(Exception("Parameter 'functionArgs' not found"))

    function_name = data['functionName']
    function_args = data['functionArgs']

    # Call interceptor if exists
    interceptor_method = getattr(remote, function_name, None)
    if not callable(interceptor_method):
        raise(Exception("Method not found or not callable: {}".format(function_name)))

    try:
        to_return = interceptor_method(function_args)
        exception_traceback = None
    except:
        to_return = None
        exception_traceback = traceback.format_exc()
        logging.exception("Exception detected when calling interceptor")

    import time
    time.sleep(1)

    return jsonify({'ret': to_return, 'exc': exception_traceback})


if __name__ == '__main__':
    app.run()
