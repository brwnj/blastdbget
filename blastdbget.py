import click
import fileinput
import ftplib
import itertools
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from distutils.spawn import find_executable


REQUIRES = ['md5sum', 'tar', 'wget']
BLAST_URL = 'ftp.ncbi.nlm.nih.gov'
BLAST_PATH = 'blast/db'


class MissingFile(Exception):
    pass


@contextmanager
def ftp_connect(url, user='anonymous', password='password'):
    connection = False
    try:
        connection = ftplib.FTP(url, user, password)
        yield connection
    finally:
        if connection:
            connection.close()


def log(category, message, *args, **kwargs):
    click.echo('%s: %s' % (
        click.style(category.ljust(10), fg='cyan'),
        message.replace('{}', click.style('{}', fg='yellow')).format(
            *args, **kwargs),
    ))


def check_dependencies(executables):
    for exe in executables:
        if not find_executable(exe):
            sys.exit("`%s` not found in PATH." % exe)


def safe_makedir(dname):
    """
    >>> import os
    >>> import shutil
    >>> test_dir = "ttttest"
    >>> safe_makedir(test_dir)
    'ttttest'
    >>> test_dir in os.listdir(".")
    True
    >>> shutil.rmtree(test_dir)
    """
    if not dname:
        return dname
    num_tries = 0
    max_tries = 5
    while not os.path.exists(dname):
        try:
            os.makedirs(dname)
        except OSError:
            if num_tries > max_tries:
                raise
            num_tries += 1
            time.sleep(2)
    return dname


def file_list(url, path=None):
    """
    >>> import ftplib
    >>> from contextlib import contextmanager
    >>> file_list("ftp.ncbi.nlm.nih.gov", "blast/demo/benchmark/2008")
    ['benchmark.tar.gz', 'benchmark.zip']
    """
    files = []
    with ftp_connect(url) as ftp:
        if path:
            ftp.cwd(path)
        try:
            files = ftp.nlst()
        except ftplib.error_perm, resp:
            if str(resp) == "550 No files found":
                raise click.UsageError('No files under %s/%s' % (ftp, path))
            else:
                raise
    return files


def show_available(files):
    available = set([f.partition(".")[0] for f in files if f.endswith(".gz")])
    available = list(available)
    available.sort()
    log('Usage', 'Set `-d` to an available database: \n{}',
        "\n".join(available))
    sys.exit(1)


def filter_file_list(files, targets):
    """
    >>> import re
    >>> files = ['est.tar.gz', 'nr.00.tar.gz', 'wgs.00.tar.gz', 'est_others.tar.gz', 'nt.00.tar.gz']
    >>> targets = ['est', 'nr']
    >>> filter_file_list(files, targets)
    ['est.tar.gz', 'nr.00.tar.gz']
    """
    p = re.compile('^(%s)\..*(tar.gz|tar.gz.md5)$' % "|".join(targets))
    return [f for f in files if p.match(f)]


def build_commands(files):
    wget_cmds = []
    md5_cmds = []
    tar_cmds = []
    for f in files:
        cmd = "wget -q {url}/{dir}/{name} 2> /dev/null".format(url=BLAST_URL,
            dir=BLAST_PATH, name=f)
        wget_cmds.append(cmd)

        if f.endswith(".gz"):
            tar_cmds.append("tar -xzf " + f)

        if f.endswith(".md5"):
            md5_cmds.append("md5sum -c " + f + " > /dev/null")

    if len(wget_cmds) != len(md5_cmds) + len(tar_cmds):
        raise MissingFile("The MD5 files should equal the number of archives.")

    return wget_cmds, md5_cmds, tar_cmds


def execute_cmds(cmd_list, n=1):
    with click.progressbar(cmd_list, label="Jobs Ran + Running") as cmds:
        groups = [(subprocess.Popen(cmd, shell=True) for cmd in cmds)] * n
        for processes in itertools.izip_longest(*groups):
            for p in filter(None, processes):
                p.wait()


def fix_md5s(files):
    """
    Some of the MD5s (at present) contain paths outside of the current
    directory which is undesirable. This removes the path and leaves the file
    name in place, ensuring `md5sum -c` has a chance to check the right file.
    """
    for f in files:
        if not f.endswith(".md5"): continue
        try:
            # strip path from md5 file name
            for toks in fileinput.input(f, mode='rU', inplace=True):
                toks = toks.rstrip("\r\n").split()
                md5sum = toks[0]
                file_name = os.path.basename(toks[1])
                # double space is intentional and required
                print "  ".join([md5sum, file_name])
        finally:
            fileinput.close()
    return files


def cleanup(files):
    for f in files:
        os.remove(f)


def is_mount(path):
    assert path.startswith('/')
    dirs = path.split('/')
    # remove initial slash from list
    dirs.remove('')
    # add slash back onto first entry
    dirs[0] = '/' + dirs[0]
    root = dirs[0]
    for i in range(len(dirs) - 1):
        path = os.path.join(root, dirs[i])
        if os.path.ismount(path):
            return True
        root = path
    return False


@click.command()
@click.argument('output', required=False, type=click.Path())
@click.option('-d', '--database', multiple=True,
              help='Databases to download, eg. "-d nr". Not specifying will '
              'list the available databases. To add multiple databases, use '
              'this parameter multiple times.')
@click.option('-t', '--threads', type=int, default=8, show_default=True,
              help='The number of concurrent processes (downloads, '
              'extractions, etc.)')
def download(output, database, threads):
    """
    Downloads listed databases to the output/<date> folder, validates downloads
    using md5sum, extracts .tar.gz files, then cleans up the output folder.
    """
    check_dependencies(REQUIRES)

    # get the contents of the remote blast dir
    log('Info', 'Communicating with Blast server')
    remote_files = file_list(BLAST_URL, BLAST_PATH)

    if not database:
        show_available(remote_files)

    # output must point to a mounted location
    if output is None:
        output = os.path.abspath('.')
    else:
        output = os.path.abspath(output)

    if not is_mount(output):
        sys.exit("Output directory (%s) is not on a mounted volume." % output)

    log('Info', 'Using {} as parent directory', output)

    # filter the list for only what we want
    to_download = filter_file_list(remote_files, database)
    total_files = len(to_download)
    total_archives = total_files / 2
    if total_files == 0:
        log('Error', 'No matches found among {}', database)
        sys.exit(1)

    log('Info', 'Found {} files matching databases: [{}]', total_files,
        ', '.join(database))

    # to better take advantage of how we're parallelizing jobs
    # groups by .gz and .md5
    to_download.sort(key=lambda x: os.path.splitext(x)[1])
    wget_cmds, md5_cmds, tar_cmds = build_commands(to_download)

    # create local directory structure and start working there
    today = time.strftime("%Y-%m-%d")
    # TODO: consider removing existing .tar.gz files
    results = safe_makedir(os.path.join(output, today))
    os.chdir(results)

    log('Info', 'Downloading {} files', len(to_download))
    execute_cmds(wget_cmds, threads)
    # file paths containing NIH directory structure stripped to basename
    fix_md5s(to_download)
    log('Info', 'Validating {} archives', total_archives)
    execute_cmds(md5_cmds, threads)
    log('Info', 'Extracting {} archives', total_archives)
    execute_cmds(tar_cmds, threads)

    # delete ".tar.gz" and ".tar.gz.md5"
    log('Info', 'Cleaning up tar files')
    cleanup(to_download)

    # symlink most recent DB to "latest"
    os.chdir(output)
    latest_dir = os.path.join(output, "latest")
    if os.path.exists(latest_dir):
        os.unlink(latest_dir)
    os.symlink(results, "latest")

    log('Complete', 'Files available at {}', latest_dir)

if __name__ == '__main__':
    download()
