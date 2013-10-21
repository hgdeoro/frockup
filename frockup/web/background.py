import logging

from multiprocessing import Process, Pipe
import os
from frockup.common import Context
from frockup.file_filter import FileFilter
from frockup.local_metadata import LocalMetadata
from frockup.main import _should_process_file

# Messages
LAUNCH_BACKUP = 'launch'
GET_STATUS = 'get_status'
STOP_ALL_PROCESSES = 'stop_all_processes'

PROCESS_STARTED = 'STARTED'
PROCESS_FINISH_OK = 'FINISH_OK'
PROCESS_FINISH_WITH_ERROR = 'FINISH_WITH_ERROR'
PROCESS_CANCELLED = 'PROCESS_CANCELLED'

#
# Standard response:
#  - ok (boolean)
#  - error (boolean)
#  - message (string)
#


def get_ok_response(status_msg, **kwargs):
    """Utility method to generate *successfull* response"""
    response = {'ok': True, 'error': False, 'message': status_msg}
    response.update(**kwargs)
    return response


def get_error_response(error_msg, **kwargs):
    """Utility method to generate *failed* response"""
    response = {'ok': False, 'error': True, 'message': error_msg}
    response.update(**kwargs)
    return response


class ProcessController(object):

    def __init__(self):
        # The controller, who launch and manitains hanlders processes
        self.process_controller = None
        # Connection used to send commands to controller
        self.parent_conn = None

    def start(self):
        """
        Starts the process.
        This method is invoked in the WEB tier.
        """
        logging.info("start()")
        self.parent_conn, child_conn = Pipe()
        self.process_controller = Process(target=self.loop, args=(child_conn,))
        self.process_controller.start()

    # Utility method - hides implementation details
    def get_background_process_status(self):
        """
        Get data about running process.
        This method is invoked in the WEB tier.
        """
        data = self.send_msg({'action': GET_STATUS})
        return data

    # Utility method - hides implementation details
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

    # Utility method - hides implementation details
    def stop_all_processes(self):
        """
        Stop all running processes.
        This method is invoked in the WEB tier.
        """
        data = self.send_msg({'action': STOP_ALL_PROCESSES})
        return data

    def send_msg(self, msg):
        """
        Sends a message and wait for the response
        This is a LOW LEVEL method. There are other methods that
        encasulates the call to this method

        The serialization/deserialization is done
        by the *multiprocessing* framework.

        This method is invoked in the WEB tier.
        This method is the entry point to communicate with the
        """
        logging.debug("send_msg() - msg: %s", msg)
        # Check first subprocess is alive
        if not self.process_controller.is_alive():
            logging.warn("process_controller is NOT alive!")
            return get_error_response('First subprocess is NOT alive.')
        self.parent_conn.send(msg)
        data = self.parent_conn.recv()
        return data

    def loop(self, child_conn):
        """
        This method is the 'target' method of `self.process_controller`.
        This methods has a loop, receives the messages and call `_handle_message()`
        This method is invoked in the FIRST SUBPROCESS (others sub-sub-processes
        are the processes that do the actual work, like uploading files).

        Returns 'response', generated by `get_ok_response()` or `get_error_response()`.
        """
        logging.info("loop()")

        background_processes_in_child = []
        finished_background_process = []

        def _loop():
            try:
                data = child_conn.recv()
                ret = self._handle_message(background_processes_in_child, data)
                child_conn.send(ret)
            except:
                logging.exception("Exception detected when handling request")
                child_conn.send(get_error_response(
                    "Exception detected when handling request"))

        try:
            while True:
                if child_conn.poll(2):
                    _loop()
                self._handle_cleanup(background_processes_in_child, finished_background_process)
        except:
            logging.exception("Exception detected in main loop of subprocess_handler()")
            raise

    def _handle_message(self, background_processes_in_child, data):
        """
        Handles a message.
        Returns 'response', generated by `get_ok_response()` or `get_error_response()`.
        """
        logging.info("_handle_message(): {}".format(data))

        #
        # LAUNCH_BACKUP
        #

        if data['action'] == LAUNCH_BACKUP:
            _parent_conn, _child_conn = Pipe()
            new_process = Process(target=action_upload_directory, args=(_child_conn,
                data['directory']))
            new_process.start()
            background_processes_in_child.append({
                                       'p': new_process,
                                       'child_conn': _child_conn,
                                       'parent_conn': _parent_conn,
                                       'status': None,
                                       'directory': data['directory'],
                                       })
            return get_ok_response('Backup process launched')

        #
        # GET_STATUS
        #

        if data['action'] == GET_STATUS:
            ret = get_ok_response('{} process running'.format(len(background_processes_in_child)))
            proc_status = []
            for item in background_processes_in_child:
                proc_status.append({'pid': item['p'].pid, 'status': item['status'],
                    'directory': item['directory']})
            ret['proc_status'] = proc_status
            return ret

        #
        # STOP_ALL_PROCESSES
        #

        if data['action'] == STOP_ALL_PROCESSES:
            all_stopped = True
            for item in background_processes_in_child:
                if not item['p'].is_alive():
                    logging.info("Won't send STOP to process {} - It's NOT alive".format(
                        item['p'].pid))

                logging.info("Will send STOP to process {}".format(item['p'].pid))
                try:
                    item['parent_conn'].send('STOP')
                except:
                    all_stopped = False
                    logging.exception("STOP_ALL_PROCESSES: exception detected when "
                        "sending STOP to process {}".format(item['p'].pid))
            if all_stopped:
                return get_ok_response('Stop sent to all the processes')
            else:
                return get_error_response("Couldn't send STOP to all processes")

        #
        # (unknown)
        #

        return get_error_response("Unknown action: '{}'".format(data['action']))

    def _handle_cleanup(self, background_processes_in_child, finished_background_process):
        logging.debug("_handle_cleanup()")
        for a_process in background_processes_in_child:
            if a_process['parent_conn'].poll():
                a_process['status'] = a_process['parent_conn'].recv()
            if not a_process['p'].is_alive():
                finished_background_process.append(
                    background_processes_in_child.remove(a_process))


#===============================================================================
# Actions
#-------------------------------------------------------------------------------
# Actions are the thins that should be done in subprocess and monitor upon completion
#===============================================================================

def action_upload_directory(_child_conn, directory):
    """
    Uploads a directory.
    """
    logger = logging.getLogger('action_upload_directory[{}]'.format(os.getpid()))
    try:
        logger.info("action_upload_directory(directory=%s)", directory)
        _child_conn.send(PROCESS_STARTED)

        ctx = Context()
        ctx.set_include_extensions(('jpg',))
        file_filter = FileFilter(ctx)
        local_metadata = LocalMetadata(ctx)

        file_list_to_proc = []
        for a_file in os.listdir(directory):
            if not os.path.isfile(os.path.join(directory, a_file)):
                continue
            should_proc, _ = _should_process_file(
                directory, a_file, file_filter, local_metadata, ctx)
            if should_proc:
                file_list_to_proc.append(a_file)

        msg_template = "Uploading file {} of {}"
        import time
        time.sleep(5)
        try:
            for i in range(0, len(file_list_to_proc)):
                if _child_conn.poll():
                    received = _child_conn.recv()
                    if received == 'STOP':
                        _child_conn.send(PROCESS_CANCELLED)
                        return
                    else:
                        logger.warn("Ignoring received text '{}'".format(received))
                _child_conn.send(msg_template.format(i, len(file_list_to_proc)))
                time.sleep(2)
            _child_conn.send(PROCESS_FINISH_OK)
        except:
            _child_conn.send(PROCESS_FINISH_WITH_ERROR)
    except:
        logger.exception("Exception detected")
        raise
