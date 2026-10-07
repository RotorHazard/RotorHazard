#
# Shared admin-authentication check
#
# Kept separate from server.py (rather than defined there) so RHUI.py can
# reuse the exact same check for plugin-registered SocketIO handlers
# (RHAPI.socket_listen -> RHUI.socket_listen) without a circular import:
# server.py imports RHUI, so RHUI can't import back from server.py.
#
import functools
import logging
from flask import request, session

logger = logging.getLogger(__name__)

Auth_succeeded_flag = False

# cached copy of GENERAL/ADMIN_SOCKET_AUTH; kept in sync by server.py's
# 'on_set_config' handler via set_admin_socket_auth_enabled()
_admin_socket_auth_enabled = True

def set_admin_socket_auth_enabled(enabled):
    global _admin_socket_auth_enabled
    _admin_socket_auth_enabled = enabled

def check_auth(racecontext, auth):
    '''Check if a username password combination is valid.'''
    global Auth_succeeded_flag
    # allow open access if both ADMIN fields set to empty string
    if not racecontext.serverconfig.get_item('SECRETS', 'ADMIN_USERNAME') and \
        not racecontext.serverconfig.get_item('SECRETS', 'ADMIN_PASSWORD'):
        Auth_succeeded_flag = True
        return True

    # allow open access if no config has been set:
    if racecontext.serverconfig.config_file_status == 0:
        Auth_succeeded_flag = True
        return True

    # allow access if user/password match
    if auth is not None and \
            auth.username == racecontext.serverconfig.get_item('SECRETS', 'ADMIN_USERNAME') and \
            auth.password == racecontext.serverconfig.get_item('SECRETS', 'ADMIN_PASSWORD'):
        Auth_succeeded_flag = True
        return True
    return False

def socketio_auth_ok(racecontext):
    '''True if the current SocketIO connection passes the admin-auth check that guarded handlers apply.'''
    if not _admin_socket_auth_enabled or session.get('socketio_admin_auth'):
        return True
    if not check_auth(racecontext, request.authorization):
        return False
    session['socketio_admin_auth'] = True
    return True

def make_socketio_auth_guard(racecontext):
    '''Returns a decorator that guards a SocketIO handler with the shared admin-auth check.

    Unlike an HTTP 401, this cannot send a response back over an
    established SocketIO connection, so it just logs and drops the
    event instead of invoking the handler.

    Some handler functions are also called directly (as plain Python
    calls, not via a dispatched SocketIO event) from server startup and
    background-thread code, which has no Flask request context. In that
    case `request.authorization` raises RuntimeError; treat that as a
    trusted internal call and let it through unchecked.

    A successful check is cached in the SocketIO connection's own
    session (separate from the browser's HTTP cookie session; reset on
    disconnect/reload) so later events on the same connection don't
    re-validate the Basic Auth header. That header is a fixed pair
    cached by the browser and can't be refreshed mid-connection, so if
    admin credentials are changed via one guarded event, live-rechecking
    every subsequent event against the new credentials would reject the
    browser's now-stale header and lock the page out for the rest of
    that connection.

    Can be turned off via the 'Admin Socket Auth' setting (Advanced
    Settings | HTTP Server), which sets GENERAL/ADMIN_SOCKET_AUTH to
    False.
    '''
    def requires_socketio_auth(f):
        @functools.wraps(f)
        def decorated_auth(*args, **kwargs):
            if not _admin_socket_auth_enabled:
                return f(*args, **kwargs)
            try:
                auth = request.authorization
            except RuntimeError:
                return f(*args, **kwargs)
            if session.get('socketio_admin_auth'):
                return f(*args, **kwargs)
            if not check_auth(racecontext, auth):
                logger.warning("Rejected unauthenticated SocketIO event '%s' from %s",
                                f.__name__, request.remote_addr)
                racecontext.rhui.emit_priority_message(
                    racecontext.language.__('Action requires authentication.'), False, nobroadcast=True)
                return
            session['socketio_admin_auth'] = True
            return f(*args, **kwargs)
        return decorated_auth
    return requires_socketio_auth

def make_socketio_credential_guard(racecontext):
    '''Returns a decorator guarding a SocketIO handler that discloses a stored credential.
    Same check as 'make_socketio_auth_guard()', except the 'Admin Socket Auth' setting does
    not bypass it (that setting relaxes action authorization, not credential disclosure),
    and there is no trusted-internal-call passthrough, so a missing request context is
    refused rather than allowed through.
    '''
    def requires_socketio_credential_auth(f):
        @functools.wraps(f)
        def decorated_auth(*args, **kwargs):
            try:
                auth = request.authorization
                remote_addr = request.remote_addr
            except RuntimeError:
                logger.warning("Refused credential SocketIO event '%s': no request context",
                               f.__name__)
                return
            if not session.get('socketio_admin_auth'):
                if not check_auth(racecontext, auth):
                    logger.warning("Rejected unauthenticated credential SocketIO event '%s' from %s",
                                   f.__name__, remote_addr)
                    racecontext.rhui.emit_priority_message(
                        racecontext.language.__('Action requires authentication.'), False, nobroadcast=True)
                    return
                # Cache the check on this connection, as the action guard does; the
                #  Basic Auth header is only sent while SocketIO uses HTTP polling, so
                #  a valid admin could otherwise be refused after the WebSocket upgrade.
                session['socketio_admin_auth'] = True
            return f(*args, **kwargs)
        return decorated_auth
    return requires_socketio_credential_auth
