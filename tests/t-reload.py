import os, sys, time, signal

try:
    import thread
except ImportError:
    import dummy_thread as thread

# This import does nothing, but it's necessary to avoid some race conditions
# in the threading module. See http://code.djangoproject.com/ticket/2330 .
try:
    import threading
except ImportError:
    pass

try:
    import termios
except ImportError:
    termios = None

RUN_RELOADER = True

_mtimes = {}
_win = (sys.platform == "win32")

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

# Change this to change monitor files
monitor_files = [CUR_DIR, ]

def code_changed_inner_python_code():
    global _mtimes, _win
    for filename in filter(lambda v: v, map(lambda m: getattr(m, "__file__", None), sys.modules.values())):
        if filename.endswith(".pyc") or filename.endswith(".pyo"):
            filename = filename[:-1]
        if filename.endswith("$py.class"):
            filename = filename[:-9] + ".py"
        if not os.path.exists(filename):
            continue # File might be in an egg, so it can't be reloaded.
        stat = os.stat(filename)
        mtime = stat.st_mtime
        if _win:
            mtime -= stat.st_ctime
        if filename not in _mtimes:
            _mtimes[filename] = mtime
            continue
        if mtime != _mtimes[filename]:
            _mtimes = {}
            return True
    return False

def code_changed():
    global _mtimes, _win
    for fn in monitor_files:
        stat = os.stat(fn)
        mtime = stat.st_mtime
        if _win:
            mtime -= stat.st_ctime
        if fn not in _mtimes:
            _mtimes[fn] = mtime
            continue
        if mtime != _mtimes[fn]:
            _mtimes = {}
            return True
    return False

def ensure_echo_on():
    if termios:
        fd = sys.stdin
        if fd.isatty():
            attr_list = termios.tcgetattr(fd)
            if not attr_list[3] & termios.ECHO:
                attr_list[3] |= termios.ECHO
                if hasattr(signal, 'SIGTTOU'):
                    old_handler = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
                else:
                    old_handler = None
                termios.tcsetattr(fd, termios.TCSANOW, attr_list)
                if old_handler is not None:
                    signal.signal(signal.SIGTTOU, old_handler)

def reloader_thread():
    ensure_echo_on()
    while RUN_RELOADER:
        if code_changed():
            sys.exit(3) # force reload
        time.sleep(1)

def restart_with_reloader():
    while True:
        args = [sys.executable] + ['-W%s' % o for o in sys.warnoptions] + sys.argv
        if sys.platform == "win32":
            args = ['"%s"' % arg for arg in args]
        new_environ = os.environ.copy()
        new_environ["RUN_MAIN"] = 'true'
        # 'os.P_WAIT' will wait until process exit.
        exit_code = os.spawnve(os.P_WAIT, sys.executable, args, new_environ)
        if exit_code != 3:
            return exit_code

def python_reloader(main_func, args, kwargs):
    if os.environ.get("RUN_MAIN") == "true":
        thread.start_new_thread(main_func, args, kwargs)
        try:
            reloader_thread()
        except KeyboardInterrupt:
            pass
    else:
        # first time run in there, and spawnve a process to handle with code_changed case.
        try:
            exit_code = restart_with_reloader()
            if exit_code < 0:
                os.kill(os.getpid(), -exit_code)
            else:
                sys.exit(exit_code)
        except KeyboardInterrupt:
            pass

def jython_reloader(main_func, args, kwargs):
    from _systemrestart import SystemRestart
    thread.start_new_thread(main_func, args)
    while True:
        if code_changed():
            raise SystemRestart
        time.sleep(1)


def main(main_func, args=None, kwargs=None):
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    if sys.platform.startswith('java'):
        reloader = jython_reloader
    else:
        reloader = python_reloader
    reloader(main_func, args, kwargs)

