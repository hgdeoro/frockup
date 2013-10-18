from flask import Flask, jsonify, request, json
import traceback
import logging
import os
import random

app = Flask(__name__)
app.debug = True


class Remote(object):

    def load_directory(self, function_args):
        base_dir = function_args[0]
        assert os.path.exists(base_dir)

        directories = []
        files = {}
        for root, _, files in os.walk(base_dir):
            directory = {
                'name': root,
                'files': files,
                'files_count': len(files),
                'ignored_count': random.randint(4, 15),
                'updated_count': random.randint(4, 15),
                'pending_count': random.randint(0, 10),
            }
            directories.append(directory)

        return {'directories': directories}


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

    return jsonify({'ret': to_return, 'exc': exception_traceback})


if __name__ == '__main__':
    app.run()
