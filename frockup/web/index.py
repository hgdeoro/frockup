import traceback
import logging
import os

from flask import Flask, jsonify, request, json

from frockup.file_filter import FileFilter
from frockup.common import Context
from frockup.main import _should_process_file
from frockup.local_metadata import LocalMetadata
from frockup.web.background import ACTION_GET_STATUS, start, ACTION_LAUNCH

app = Flask(__name__)
app.debug = True

parent_conn = None


class Remote(object):

    def __init__(self):
        self.ctx = Context()
        self.ctx.set_include_extensions(('jpg',))

        self.file_filter = FileFilter(self.ctx)

        self.local_metadata = LocalMetadata(self.ctx)

    def get_background_process_status(self, function_args):
        parent_conn.send({'action': ACTION_GET_STATUS})
        data = parent_conn.recv()
        return {'message': data}

    def launch_process(self, function_args):
        parent_conn.send({'action': ACTION_LAUNCH, 'directory': 'd', 'filename': 'f'})
        data = parent_conn.recv()
        return data

    def load_directory(self, function_args):
        base_dir = function_args[0]
        assert os.path.exists(base_dir)

        directories = []
        files = {}
        for root, _, files in os.walk(base_dir):
            self.local_metadata._opendb(root)
            file_list = []
            ignored_count = 0
            updated_count = 0
            pending_count = 0
            for a_file in files:
                should_proc, _ = _should_process_file(root, a_file, self.file_filter,
                                                      self.local_metadata, self.ctx)
                if should_proc:
                    pending_count += 1

            directory = {
                'name': root,
                'files': files,
                'files_count': len(files),
                'file_list': file_list,
                'ignored_count': ignored_count,
                'updated_count': updated_count,
                'pending_count': pending_count,
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
    logging.basicConfig(level=logging.INFO)
    parent_conn = start()
    app.run()
