import logging

from multiprocessing import Process, Pipe
import os


LAUNCH_BACKUP = 'launch'
ACTION_GET_STATUS = 'get_status'

PROCESS_STARTED = 'STARTED'
PROCESS_FINISH_OK = 'FINISH_OK'
PROCESS_FINISH_WITH_ERROR = 'FINISH_WITH_ERROR'


class ProcessController(object):

    def __init__(self):
        # Connection used to send commands to controller
        self.parent_conn = None
        # The controller, who launch and manitains hanlders processes
        self.process_controller = None
        # The child processes launched for handling the requested actions
        self.background_processes_in_child = []
        # List of finished processes pending to be informed
        self.finished_background_process = []

    def start(self):
        """
        Starts the process.
        This method is invoked in the WEB tier.
        """
        logging.info("start()")
        self.parent_conn, child_conn = Pipe()
        self.process_controller = Process(target=self.loop, args=(child_conn,))
        self.process_controller.start()

    def get_background_process_status(self):
        """
        Get data about running process
        This method is invoked in the WEB tier.
        """
        data = self.send_msg({'action': ACTION_GET_STATUS})
        return data

    def launch_backup(self, directory_name):
        """
        Launch the backup of a directory.
        This method is invoked in the WEB tier.
        """
        # TODO: rename to 'sync_directory()' or something else
        assert os.path.exists(directory_name)
        data = self.send_msg({'action': LAUNCH_BACKUP,
            'directory': directory_name})
        return data

    def send_msg(self, msg):
        """
        Sends a message and wait for the response
        This is a LOW LEVEL method. There are other methods that
        encasulates the call to this method

        This method is invoked in the WEB tier.
        This method is the entry point to communicate with the
        """
        logging.debug("send_msg() - msg: %s", msg)
        self.parent_conn.send(msg)
        data = self.parent_conn.recv()
        return data

    def loop(self, child_conn):
        """
        This method is the 'target' method of `self.process_controller`.
        This methods has a loop, receives the messages and call `_handle_message()`
        This method is invoked in the FIRST SUBPROCESS (others sub-sub-processes
        are the processes that do the actual work, like uploading files)
        """
        logging.info("loop()")

        try:
            while True:
                poll_ok = child_conn.poll(2)
                if poll_ok:
                    data = child_conn.recv()
                    try:
                        ret = self._handle_message(data)
                        child_conn.send(ret)
                    except:
                        logging.exception("Exception detected when handling request")
                        child_conn.send('action_returned_error')
                self._handle_cleanup()
        except:
            logging.exception("Exception detected in main loop of subprocess_handler()")

    def _handle_message(self, data):
        logging.info("_handle_message(): {}".format(data))

        if data['action'] == LAUNCH_BACKUP:
            _parent_conn, _child_conn = Pipe()
            new_process = Process(target=action_upload_file, args=(_child_conn,
                data['directory']))
            new_process.start()
            self.background_processes_in_child.append({
                                       'p': new_process,
                                       'child_conn': _child_conn,
                                       'parent_conn': _parent_conn,
                                       'status': None,
                                       })
            return 'launched'

        if data['action'] == ACTION_GET_STATUS:
            return '{} process running'.format(len(self.background_processes_in_child))

        return 'action_unknown'

    def _handle_cleanup(self):
        logging.debug("_handle_cleanup()")
        for a_process in self.background_processes_in_child:
            if a_process['parent_conn'].poll():
                a_process['status'] = a_process['parent_conn'].recv()
            if not a_process['p'].is_alive():
                self.finished_background_process.append(
                    self.background_processes_in_child.remove(a_process))


#===============================================================================
# Actions
#-------------------------------------------------------------------------------
# Actions are the thins that should be done in subprocess and monitor upon completion
#===============================================================================

def action_upload_file(_child_conn, directory):
    """
    Uploads a file.
    """
    logging.info("action_upload_file(directory=%s)", directory)
    _child_conn.send(PROCESS_STARTED)
    try:
        import time
        time.sleep(120)
        _child_conn.send(PROCESS_FINISH_OK)
    except:
        _child_conn.send(PROCESS_FINISH_WITH_ERROR)
