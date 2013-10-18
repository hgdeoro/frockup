import logging

from multiprocessing import Process, Pipe


parent_conn = None
background_process = []
finished_background_process = []

ACTION_LAUNCH = 'launch'
ACTION_GET_STATUS = 'get_status'

STARTED = 'STARTED'
FINISH_OK = 'FINISH_OK'


def start():
    logging.info("start()")
    global parent_conn
    global background_process
    parent_conn, child_conn = Pipe()
    background_process = Process(target=subprocess_handler, args=(child_conn,))
    background_process.start()
    return parent_conn


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
