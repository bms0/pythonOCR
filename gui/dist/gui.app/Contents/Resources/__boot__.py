def _reset_sys_path():
    # Clear generic sys.path[0]
    import os
    import sys

    resources = os.environ["RESOURCEPATH"]
    while sys.path[0] == resources:
        del sys.path[0]


_reset_sys_path()


def _emulate_shell_environ():
    import os
    import sys
    import time

    if sys.version_info[0] > 2:
        env = os.environb
    else:
        env = os.environ

    split_char = b"="

    # Start 'login -qf $LOGIN' in a pseudo-tty. The pseudo-tty
    # is required to get the right behavior from the shell, without
    # a tty the shell won't properly initialize the environment.
    #
    # NOTE: The code is very carefull w.r.t. getting the login
    # name, the application shouldn't crash when the shell information
    # cannot be retrieved
    try:
        login = os.getlogin()
        if login == "root":
            # For some reason os.getlogin() returns
            # "root" for user sessions on Catalina.
            try:
                login = os.environ["LOGNAME"]
            except KeyError:
                login = None
    except AttributeError:
        try:
            login = os.environ["LOGNAME"]
        except KeyError:
            login = None

    if login is None:
        return

    master, slave = os.openpty()
    pid = os.fork()

    if pid == 0:
        # Child
        os.close(master)
        os.setsid()
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        os.execv("/usr/bin/login", ["login", "-qf", login])
        os._exit(42)

    else:
        # Parent
        os.close(slave)
        # Echo markers around the actual output of env, that makes it
        # easier to find the real data between other data printed
        # by the shell.
        os.write(master, b'echo "---------";env;echo "-----------"\r\n')
        os.write(master, b"exit\r\n")
        time.sleep(1)

        data = []
        b = os.read(master, 2048)
        while b:
            data.append(b)
            b = os.read(master, 2048)
        data = b"".join(data)
        os.waitpid(pid, 0)

    in_data = False
    for ln in data.splitlines():
        if not in_data:
            if ln.strip().startswith(b"--------"):
                in_data = True
            continue

        if ln.startswith(b"--------"):
            break

        try:
            key, value = ln.rstrip().split(split_char, 1)
        except Exception:
            pass

        else:
            env[key] = value


_emulate_shell_environ()


def _chdir_resource():
    import os

    os.chdir(os.environ["RESOURCEPATH"])


_chdir_resource()


def _disable_linecache():
    import linecache

    def fake_getline(*args, **kwargs):
        return ""

    linecache.orig_getline = linecache.getline
    linecache.getline = fake_getline


_disable_linecache()


import re
import sys

cookie_re = re.compile(br"coding[:=]\s*([-\w.]+)")
if sys.version_info[0] == 2:
    default_encoding = "ascii"
else:
    default_encoding = "utf-8"


def guess_encoding(fp):
    for _i in range(2):
        ln = fp.readline()

        m = cookie_re.search(ln)
        if m is not None:
            return m.group(1).decode("ascii")

    return default_encoding


def _run():
    global __file__
    import os
    import site  # noqa: F401

    sys.frozen = "macosx_app"
    base = os.environ["RESOURCEPATH"]

    argv0 = os.path.basename(os.environ["ARGVZERO"])
    script = SCRIPT_MAP.get(argv0, DEFAULT_SCRIPT)  # noqa: F821

    path = os.path.join(base, script)
    sys.argv[0] = __file__ = path
    if sys.version_info[0] == 2:
        with open(path, "rU") as fp:
            source = fp.read() + "\n"
    else:
        with open(path, "rb") as fp:
            encoding = guess_encoding(fp)

        with open(path, "r", encoding=encoding) as fp:
            source = fp.read() + "\n"

        BOM = b"\xef\xbb\xbf".decode("utf-8")
        if source.startswith(BOM):
            source = source[1:]

    exec(compile(source, path, "exec"), globals(), globals())


def _recipes_pil_prescript(plugins):
    try:
        import Image

        have_PIL = False
    except ImportError:
        from PIL import Image

        have_PIL = True

    import sys

    def init():
        if Image._initialized >= 2:
            return

        if have_PIL:
            try:
                import PIL.JpegPresets

                sys.modules["JpegPresets"] = PIL.JpegPresets
            except ImportError:
                pass

        for plugin in plugins:
            try:
                if have_PIL:
                    try:
                        # First try absolute import through PIL (for
                        # Pillow support) only then try relative imports
                        m = __import__("PIL." + plugin, globals(), locals(), [])
                        m = getattr(m, plugin)
                        sys.modules[plugin] = m
                        continue
                    except ImportError:
                        pass

                __import__(plugin, globals(), locals(), [])
            except ImportError:
                print("Image: failed to import")

        if Image.OPEN or Image.SAVE:
            Image._initialized = 2
            return 1

    Image.init = init


_recipes_pil_prescript(['QoiImagePlugin', 'BufrStubImagePlugin', 'PixarImagePlugin', 'EpsImagePlugin', 'SunImagePlugin', 'XpmImagePlugin', 'GifImagePlugin', 'Jpeg2KImagePlugin', 'IcoImagePlugin', 'PsdImagePlugin', 'IptcImagePlugin', 'MpegImagePlugin', 'ImImagePlugin', 'CurImagePlugin', 'SgiImagePlugin', 'WebPImagePlugin', 'PpmImagePlugin', 'ImtImagePlugin', 'FitsImagePlugin', 'MpoImagePlugin', 'XVThumbImagePlugin', 'MspImagePlugin', 'MicImagePlugin', 'BmpImagePlugin', 'DdsImagePlugin', 'PalmImagePlugin', 'PcdImagePlugin', 'FtexImagePlugin', 'GribStubImagePlugin', 'DcxImagePlugin', 'XbmImagePlugin', 'GbrImagePlugin', 'FliImagePlugin', 'IcnsImagePlugin', 'Hdf5StubImagePlugin', 'FpxImagePlugin', 'SpiderImagePlugin', 'PdfImagePlugin', 'PngImagePlugin', 'BlpImagePlugin', 'TgaImagePlugin', 'WmfImagePlugin', 'PcxImagePlugin', 'McIdasImagePlugin', 'TiffImagePlugin', 'JpegImagePlugin'])


def _setup_ctypes():
    import os
    from ctypes.macholib import dyld

    frameworks = os.path.join(os.environ["RESOURCEPATH"], "..", "Frameworks")
    dyld.DEFAULT_FRAMEWORK_FALLBACK.insert(0, frameworks)
    dyld.DEFAULT_LIBRARY_FALLBACK.insert(0, frameworks)


_setup_ctypes()


def _boot_multiprocessing():
    import sys
    import multiprocessing.spawn

    orig_get_command_line = multiprocessing.spawn.get_command_line
    def wrapped_get_command_line(**kwargs):
        orig_frozen = sys.frozen
        del sys.frozen
        try:
            return orig_get_command_line(**kwargs)
        finally:
            sys.frozen = orig_frozen
    multiprocessing.spawn.get_command_line = wrapped_get_command_line

_boot_multiprocessing()


import pkg_resources, zipimport, os

def find_eggs_in_zip(importer, path_item, only=False):
    if importer.archive.endswith('.whl'):
        # wheels are not supported with this finder
        # they don't have PKG-INFO metadata, and won't ever contain eggs
        return

    metadata = pkg_resources.EggMetadata(importer)
    if metadata.has_metadata('PKG-INFO'):
        yield Distribution.from_filename(path_item, metadata=metadata)
    for subitem in metadata.resource_listdir(''):
        if not only and pkg_resources._is_egg_path(subitem):
            subpath = os.path.join(path_item, subitem)
            dists = find_eggs_in_zip(zipimport.zipimporter(subpath), subpath)
            for dist in dists:
                yield dist
        elif subitem.lower().endswith(('.dist-info', '.egg-info')):
            subpath = os.path.join(path_item, subitem)
            submeta = pkg_resources.EggMetadata(zipimport.zipimporter(subpath))
            submeta.egg_info = subpath
            yield pkg_resources.Distribution.from_location(path_item, subitem, submeta)  # noqa: B950

def _fixup_pkg_resources():
    pkg_resources.register_finder(zipimport.zipimporter, find_eggs_in_zip)
    pkg_resources.working_set.entries = []
    list(map(pkg_resources.working_set.add_entry, sys.path))

_fixup_pkg_resources()



def _setup_openssl():
    import os
    resourcepath = os.environ["RESOURCEPATH"]
    os.environ["SSL_CERT_FILE"] = os.path.join(
        resourcepath, "openssl.ca", "no-such-file")
    os.environ["SSL_CERT_DIR"] = os.path.join(
        resourcepath, "openssl.ca", "no-such-file")

_setup_openssl()


def _boot_tkinter():
    import os

    resourcepath = os.environ["RESOURCEPATH"]
    os.putenv("TCL_LIBRARY", os.path.join(resourcepath, "lib/tcl8"))
    os.putenv("TK_LIBRARY", os.path.join(resourcepath, "lib/tk8.6"))
_boot_tkinter()


DEFAULT_SCRIPT='gui.py'
SCRIPT_MAP={}
_run()
