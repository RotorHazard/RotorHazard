# InvokeFuncQueue:  Operates an invoke-function queue

# Invokes a function sequentially, via a GEvent queue.

import gevent

class InvokeFuncQueue:
    """ Invokes a function sequentially, via a GEvent queue. """

    def __init__(self, logger, maxQueueSize=20):
        self.logger = logger
        self.invokeFuncQueue = gevent.queue.Queue(maxsize=maxQueueSize)
        self.invokeInProgressFlag = False
        gevent.spawn(self.queueWorkerFn)

    def put(self, funct, *args, **kwargs):
        try:
            self.invokeFuncQueue.put((funct, args, kwargs))
        except:
            self.logger.exception("InvokeFuncQueue 'put' error")

    def queueWorkerFn(self):
        while True:
            try:
                (funct, args, kwargs) = self.invokeFuncQueue.get()  # wait for next item in queue
                try:
                    self.invokeInProgressFlag = True
                    funct(*args, **kwargs)
                    self.invokeInProgressFlag = False
                    gevent.sleep()
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
            while self.invokeInProgressFlag or (not self.invokeFuncQueue.empty()):
                count += 1
                if count > 300:
                    self.logger.error("Timeout waiting for InvokeFuncQueue empty")
                    return
                gevent.sleep(0.01)
        except Exception:
            self.logger.exception("Error waiting for InvokeFuncQueue empty")
