import traceback
import logging
import os

from flask import Flask, jsonify, request, json

from frockup.file_filter import FileFilter
from frockup.common import Context
from frockup.main import _should_process_file
from frockup.local_metadata import LocalMetadata
from frockup.web.background import ProcessController

app = Flask(__name__)
app.debug = True

PROCESS_CONTROLLER = ProcessController()


class Remote(object):

    def __init__(self):
        self.ctx = Context()
        self.ctx.set_include_extensions(('jpg',))
        self.file_filter = FileFilter(self.ctx)
        self.local_metadata = LocalMetadata(self.ctx)
        self.logger = logging.getLogger('Remote')

    def get_background_process_status(self, function_args):
        self.logger.debug("get_background_process_status() - %s", function_args)
        data = PROCESS_CONTROLLER.get_background_process_status()
        return data

    def launch_backup(self, function_args):
        self.logger.info("launch_backup() - %s", function_args)
        directory_name = function_args[0]
        assert os.path.exists(directory_name)
        data = PROCESS_CONTROLLER.launch_backup(directory_name)
        return data

    def stop_all_processes(self, function_args):
        self.logger.info("stop_all_processes() - %s", function_args)
        data = PROCESS_CONTROLLER.stop_all_processes()
        return data

    def load_directory(self, function_args):
        base_dir = function_args[0]
        assert os.path.exists(base_dir)

        directories = []
        files = {}
        for root, _, files in os.walk(base_dir):
            try:
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
            finally:
                self.local_metadata.close()

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
    #    ch = logging.StreamHandler()
    #    ch.setLevel(logging.INFO)
    #    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #    ch.setFormatter(formatter)
    #    logging.root.addHandler(ch)
    logging.root.setLevel(logging.INFO)
    for h in logging.root.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
    logging.info("Starting...")
    PROCESS_CONTROLLER.start()
    app.run()
