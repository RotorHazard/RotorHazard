# InvokeFuncQueue:  Operates an invoke-function queue

# Invokes a function sequentially, via a GEvent queue.

import collections
import gevent
import gevent.queue

class InvokeFuncQueue:
    """ Invokes a function sequentially, via a GEvent queue. """

    def __init__(self, logger, maxQueueSize=20):
        self.logger = logger
        self.invokeFuncQueue = gevent.queue.Queue(maxsize=maxQueueSize)
        self.invokeInProgressFlag = False
        # items put by the worker while the queue is full, each with the queue-get count at which it runs
        self.workerOverflow = collections.deque()
        self.queueGetCount = 0
        self.workerGreenlet = gevent.spawn(self.queueWorkerFn)

    def put(self, funct, *args, **kwargs):
        try:
            if gevent.getcurrent() is self.workerGreenlet:
                # a put from the worker never blocks, since only the worker can free a slot
                try:
                    if not self.workerOverflow:
                        self.invokeFuncQueue.put_nowait((funct, args, kwargs))
                        return
                except gevent.queue.Full:
                    pass
                self.workerOverflow.append((self.queueGetCount + self.invokeFuncQueue.qsize(), (funct, args, kwargs)))
            else:
                self.invokeFuncQueue.put((funct, args, kwargs))
        except:
            self.logger.exception("InvokeFuncQueue 'put' error")

    def getNextItem(self):
        # runs an overflow item once the queue items that were ahead of it have been taken
        if self.workerOverflow and self.queueGetCount >= self.workerOverflow[0][0]:
            return self.workerOverflow.popleft()[1]
        item = self.invokeFuncQueue.get()  # wait for next item in queue
        self.queueGetCount += 1
        return item

    def queueWorkerFn(self):
        while True:
            try:
                (funct, args, kwargs) = self.getNextItem()
                try:
                    self.invokeInProgressFlag = True
                    funct(*args, **kwargs)
                    self.invokeInProgressFlag = False
                    gevent.sleep(0.001)
                except (KeyboardInterrupt, SystemExit):
                    self.invokeInProgressFlag = False
                    raise
                except Exception:
                    self.invokeInProgressFlag = False
                    self.logger.exception("InvokeFuncQueue error invoking function")
                    gevent.sleep(1)
            except KeyboardInterrupt:
                self.invokeInProgressFlag = False
                self.logger.info("InvokeFuncQueue worker thread terminated by keyboard interrupt")
                raise
            except SystemExit:
                self.invokeInProgressFlag = False
                raise
            except Exception:
                self.invokeInProgressFlag = False
                self.logger.exception("InvokeFuncQueue error processing queue (aborting thread)")
                break

    # waits until no function invocation is in progress and the queue is empty
    def waitForQueueEmpty(self):
        try:
            count = 0
            while self.invokeInProgressFlag or self.workerOverflow or (not self.invokeFuncQueue.empty()):
                count += 1
                if count > 300:
                    self.logger.error("Timeout waiting for InvokeFuncQueue empty")
                    return
                gevent.sleep(0.01)
        except Exception:
            self.logger.exception("Error waiting for InvokeFuncQueue empty")
