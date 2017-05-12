#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# compute/parallel.py

import logging
import multiprocessing
import threading

from tqdm import tqdm

from .. import config


def get_num_processes():
    """Return the number of processes to use in parallel."""
    cpu_count = multiprocessing.cpu_count()

    if config.NUMBER_OF_CORES == 0:
        raise ValueError(
            'Invalid NUMBER_OF_CORES; value may not be 0.')

    if config.NUMBER_OF_CORES > cpu_count:
        raise ValueError(
            'Invalid NUMBER_OF_CORES; value must be less than or '
            'equal to the available number of cores ({} for this '
            'system).'.format(cpu_count))

    if config.NUMBER_OF_CORES < 0:
        num = cpu_count + config.NUMBER_OF_CORES + 1
        if num <= 0:
            raise ValueError(
                'Invalid NUMBER_OF_CORES; negative value is too negative: '
                'requesting {} cores, {} available.'.format(num, cpu_count))

        return num

    return config.NUMBER_OF_CORES


POISON_PILL = None


# TODO: maintain a single log thread?
class LogThread(threading.Thread):
    """Thread which handles log records sent from ``MapReduce`` processes.

    It listens to an instance of ``multiprocessing.Queue``, rewriting log
    messages to the PyPhi log handler.
    """
    def __init__(self, q):
        self.q = q
        super().__init__()
        self.daemon = True

    def run(self):
        while True:
            record = self.q.get()
            if record is POISON_PILL:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)


def configure_worker_logging(queue):
    """Configure a worker process to log all messages to the given queue."""
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'queue': {
                'class': 'logging.handlers.QueueHandler',
                'queue': queue,
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['queue']
        },
    }
    logging.config.dictConfig(config)


class MapReduce:
    """
    An engine for doing heavy computations over an iterable.

    This is similar to ``multiprocessing.Pool``, but allows computations to
    shortcircuit, and supports both parallel and sequential computations.

    Args:
        iterable (Iterable): A collection of objects to perform a computation
            over.
        *context: Any additional data necessary to complete the computation.

    Any subclass of ``MapReduce`` must implement three methods::

        * ``empty_result``,
        * ``compute``, (map), and
        * ``process_result`` (reduce).

    The engine includes a builtin ``tqdm`` progress bar.
    """
    # Description for the tqdm progress bar
    description = ''

    def __init__(self, iterable, *context):
        self.iterable = list(iterable)
        self.context = context

        # Initialize progress bar
        self.progress = tqdm(total=len(self.iterable), leave=False,
                             disable=(not config.PROGRESS_BARS),
                             desc=self.description)

    def empty_result(self, obj, *context):
        """Return the default result with which to begin the computation."""
        raise NotImplementedError

    def compute(self, obj, *context):
        """Map over a single object from ``self.iterable``."""
        raise NotImplementedError

    def process_result(self, new_result, old_result):
        """Reduce handler.

        Every time a new result is generated by ``compute``, this method is
        called with the result and the previous (accumulated) result. This
        method compares or collates these two values, returning the new result.

        Setting ``self.done`` to ``True`` in this method will abort the
        remainder of the computation, returning this final result.
        """
        raise NotImplementedError

    def worker(self, in_queue, out_queue, log_queue, *context):
        """A worker process, run by ``multiprocessing.Process``."""
        configure_worker_logging(log_queue)
        while True:
            obj = in_queue.get()
            if obj is POISON_PILL:
                break
            out_queue.put(self.compute(obj, *context))
        out_queue.put(POISON_PILL)

    def init_parallel(self):
        self.number_of_processes = get_num_processes()

        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()
        self.log_queue = multiprocessing.Queue()

        # Load all objects to perform the computation over
        for obj in self.iterable:
            self.in_queue.put(obj)

        for i in range(self.number_of_processes):
            self.in_queue.put(POISON_PILL)

        args = (self.in_queue, self.out_queue, self.log_queue) + self.context
        self.processes = [
            multiprocessing.Process(target=self.worker, args=args, daemon=True)
            for i in range(self.number_of_processes)]

        self.log_thread = LogThread(self.log_queue)

    def start_parallel(self):
        """Start all processses and the log thread."""
        for process in self.processes:
            process.start()

        self.log_thread.start()

    def finish_parallel(self):
        """Terminate all processes and the log thread."""
        for process in self.processes:
            process.terminate()

        # Shutdown the log thread
        self.log_queue.put(POISON_PILL)
        # self.log_thread.join()

        # Remove the progress bar
        self.progress.close()

    def run_parallel(self):
        """Perform the computation in parallel, reading results from the output
        queue and passing them to ``process_result``.
        """
        self.init_parallel()
        self.start_parallel()

        self.done = False
        result = self.empty_result(*self.context)

        while not self.done:
            r = self.out_queue.get()
            if r is POISON_PILL:
                self.number_of_processes -= 1
                if self.number_of_processes == 0:
                    break
            else:
                result = self.process_result(r, result)
                self.progress.update(1)

        self.finish_parallel()

        return result

    def run_sequential(self):
        """Perform the computation sequentially, only holding two computed
        objects in memory at a time.
        """
        self.done = False
        result = self.empty_result(*self.context)

        for obj in self.iterable:
            r = self.compute(obj, *self.context)
            result = self.process_result(r, result)
            self.progress.update(1)

            # Short-circuited?
            if self.done:
                break

        # Remove progress bar
        self.progress.close()

        return result

    def run(self, parallel=True):
        if parallel:
            return self.run_parallel()
        else:
            return self.run_sequential()
