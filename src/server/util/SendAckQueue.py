# SendAckQueue:  Operates a send-with-acknowledge message-emit queue

# Messages are emitted via the given 'SOCKET_IO' object, using a 'gevent' queue.  Initially,
# messages are cleared from the queue as soon as they are sent.  Once an initial message-'ack'
# is received, messages are not cleared from the queue until they are 'ack'd, and they will be
# retried while waiting (up to retry-max-attempts count).

# A message may also be sent with 'waitForAckFlag'=False, in which case it will be inserted at
# the beginning of the queue and then cleared when sent (without waiting for an 'ack').  This
# is to support "join-cluster-response"-type messages that need to be sent "asynchronously"
# when a connection is re-established after a disconnect.

import gevent

class SendAckQueue:
    """ Operates a send-with-acknowledge emit queue """

    SAQ_RETRY_INTERVAL_SECS = 3
    SAQ_RETRY_MAX_ATTEMPTS = 40  # retry for about two minutes max

    def __init__(self, maxQueueSize, SOCKET_IO, logger):
        self.SOCKET_IO = SOCKET_IO
        self.logger = logger
        self.emitMessageQueue = gevent.queue.Queue(maxsize=maxQueueSize)
        self.anyAcksReceivedFlag = False
        self.ackNotifyEventObj = gevent.event.Event()
        gevent.spawn(self.queueWorkerFn)

    def put(self, messageType, messagePayload, waitForAckFlag=True):
        try:
            if waitForAckFlag or self.emitMessageQueue.empty():
                self.emitMessageQueue.put((messageType, messagePayload, waitForAckFlag), timeout=1)
            else:
                # if not waitForAck and queue not empty then put message at beginning of queue
                #  (other messages in queue will be retried and ack'd later)
                self.emitMessageQueue.queue.appendleft((messageType, messagePayload, waitForAckFlag))
                if hasattr(self.emitMessageQueue, 'getters') and self.emitMessageQueue.getters:
                    self.emitMessageQueue._schedule_unlock()
                # notify queue-worker thread to send message immediately
                self.ackNotifyEventObj.set()
        except Exception as ex:
            self.logger.error("SendAckQueue 'put' error ('{0}'); msg: '{1}': {2}".\
                         format(ex, messageType, messagePayload))

    def ack(self, messageType, messagePayload):
        try:
            if self.anyAcksReceivedFlag:
                if messagePayload:  # if payload then ack is for message currently in queue
                    if not self.emitMessageQueue.empty():
                        (qMsgType, qMsgPayload, qWaitAckFlag) = self.emitMessageQueue.peek()
                        if messageType == qMsgType:
                            if messagePayload == qMsgPayload:
                                self.emitMessageQueue.get_nowait()
                                self.ackNotifyEventObj.set()
                            else:
                                self.logger.warning("SendAckQueue received 'ack' messagePayload ('{0}') "\
                                                 "different from one in queue ('{1}')".\
                                                 format(messagePayload, qMsgPayload))
                        else:
                            self.logger.warning("SendAckQueue received 'ack' messageType ('{0}') "\
                                             "different from one in queue ('{1}')".\
                                             format(messageType, qMsgType))
                    elif messagePayload:
                        self.logger.warning("SendAckQueue received 'ack' with empty queue; msg: '{0}': {1}".\
                                         format(messageType, messagePayload))
            else:
                self.anyAcksReceivedFlag = True  # expect messages to be 'ack'd from now one
        except Exception:
            self.logger.exception("SendAckQueue error processing received 'ack' message")

    def queueWorkerFn(self):
        emitRetryCount = 0
        while True:
            try:
                (messageType, messagePayload, waitForAckFlag) = self.emitMessageQueue.peek()
                try:
                    self.ackNotifyEventObj.clear()
                    self.SOCKET_IO.emit(messageType, messagePayload)
                    if waitForAckFlag and self.anyAcksReceivedFlag:
                        if self.ackNotifyEventObj.wait(self.SAQ_RETRY_INTERVAL_SECS):
                            emitRetryCount = 0  # thread-notify received; move on to next message
                            self.ackNotifyEventObj.clear()
                        elif not self.emitMessageQueue.empty():  # retry timeout reached
                            emitRetryCount += 1
                            if emitRetryCount <= self.SAQ_RETRY_MAX_ATTEMPTS:
                                self.logger.info("SendAckQueue timeout reached (retryCount={0}); resending msg: '{1}': {2}".\
                                                 format(emitRetryCount, messageType, messagePayload))
                            else:
                                self.logger.warning("SendAckQueue retry limit reached (retryCount={0}); discarding msg: '{1}': {2}".\
                                                 format(emitRetryCount, messageType, messagePayload))
                                self.emitMessageQueue.get_nowait()
                                emitRetryCount = 0
                        else:
                            emitRetryCount = 0
                            self.logger.info("SendAckQueue empty queue after timeout reached; msg: '{0}': {1}".\
                                             format(messageType, messagePayload))
                    elif not self.emitMessageQueue.empty():  # not waiting for ack
                        self.emitMessageQueue.get_nowait()   # pop message from queue
                        emitRetryCount = 0
                        self.ackNotifyEventObj.clear()
                        gevent.sleep(0.001)  # do a slight pause before (possibly) sending next message
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception:
                    self.logger.exception("SendAckQueue error processing emit-message queue item")
                    if not self.emitMessageQueue.empty():
                        self.emitMessageQueue.get_nowait()
                    gevent.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("SendAckQueue worker thread terminated by keyboard interrupt")
                raise
            except SystemExit:
                raise
            except Exception:
                self.logger.exception("SendAckQueue error processing emit-message queue (aborting thread)")
                break
