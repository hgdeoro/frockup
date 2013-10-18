import traceback
import logging
import os

from flask import Flask, jsonify, request, json
from multiprocessing import Process, Pipe

from frockup.file_filter import FileFilter
from frockup.common import Context
from frockup.main import _should_process_file
from frockup.local_metadata import LocalMetadata

app = Flask(__name__)
app.debug = True

parent_conn = None
background_process = []
finished_background_process = []

ACTION_LAUNCH = 'launch'
ACTION_GET_STATUS = 'get_status'

STARTED = 'STARTED'
FINISH_OK = 'FINISH_OK'


def subprocess_handler(child_conn):

    logging.info("subprocess_handler()")
    background_processes_in_child = []

    def _handle_action_launch(_child_conn, directory, filename):
        logging.info("_handle_action_launch()")
        _child_conn.send(STARTED)
        import time
        time.sleep(10)
        _child_conn.send(FINISH_OK)

    def _handle_input(data):
        logging.info("_handle_input(): {}".format(data))
        if data['action'] == ACTION_LAUNCH:
            _parent_conn, _child_conn = Pipe()
            new_process = Process(target=_handle_action_launch, args=(_child_conn,
                                                                      data['directory'],
                                                                      data['filename']))
            new_process.start()
            background_processes_in_child.append({
                                       'p': new_process,
                                       'child_conn': _child_conn,
                                       'parent_conn': _parent_conn,
                                       'status': None,
                                       })
            return 'launched'

        if data['action'] == ACTION_GET_STATUS:
            return '{} process running'.format(len(background_processes_in_child))

        return 'action_unknown'

    def _handle_cleanup():
        logging.info("_handle_cleanup()")
        for a_process in background_processes_in_child:
            if a_process['parent_conn'].poll():
                a_process['status'] = a_process['parent_conn'].recv()
            if not a_process['p'].is_alive():
                finished_background_process.append(background_processes_in_child.remove(a_process))

    try:
        while True:
            poll_ok = child_conn.poll(2)
            if poll_ok:
                data = child_conn.recv()
                try:
                    ret = _handle_input(data)
                    child_conn.send(ret)
                except:
                    logging.exception("Exception detected when handling request")
                    child_conn.send('action_returned_error')
            _handle_cleanup()
    except:
        logging.exception("Exception detected in main loop of subprocess_handler()")


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
    #     global background_process
    #     global parent_conn
    logging.basicConfig(level=logging.INFO)
    parent_conn, child_conn = Pipe()
    background_process = Process(target=subprocess_handler, args=(child_conn,))
    background_process.start()
    app.run()
