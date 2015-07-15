"""
Downloads listed databases to the output folder, validates downloads
using md5, and extracts .tar.gz files.
"""

from __future__ import print_function

import argparse
import fileinput
import ftplib
import hashlib
import itertools
import logging
import os
import re
import shutil
import socket
import sys
import tarfile
import time
import urllib

from contextlib import contextmanager
from sh import blastdbcheck, ErrorReturnCode
from tempfile import mkdtemp
from threading import Thread
from Queue import Queue


BLAST_URL = 'ftp.ncbi.nlm.nih.gov'
BLAST_PATH = 'blast/db'
timeout = 10
socket.setdefaulttimeout(timeout)


class DbFile(object):
    def __init__(self, tarname, output):
        self.remotetar = "ftp://%s/%s/%s" % (BLAST_URL, BLAST_PATH, tarname)
        self.tar = "%s/%s" % (os.path.abspath(output), tarname)
        self.md5 = self.tar + ".md5"
        self.remotemd5 = self.remotetar + ".md5"
        self.retries = 0


@contextmanager
def ftp_connect(url, user='anonymous', password='password'):
    connection = False
    try:
        connection = ftplib.FTP(url, user, password)
        yield connection
    finally:
        if connection:
            connection.close()


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
    log = logging.getLogger(__name__)
    files = []
    with ftp_connect(url) as ftp:
        if path:
            ftp.cwd(path)
        try:
            files = ftp.nlst()
        except ftplib.error_perm, e:
            if str(e) == "550 No files found":
                log.error('No files under %s/%s' % (ftp, path))
                raise
            else:
                raise
        except socket.timeout:
            log.error("Failed to make a connection to %s" % ftp, exc_info=True)
    return files


def show_available(files):
    available = set([f.partition(".")[0] for f in files if f.endswith(".gz")])
    available = list(available)
    available.sort()

    print(*['Usage: Set `-d` to an available database:'] + available, sep="\n")
    sys.exit(1)


def filter_file_list(files, targets):
    """
    >>> import re
    >>> files = ['est.tar.gz', 'nr.00.tar.gz', 'wgs.00.tar.gz', 'est_others.tar.gz', 'nt.00.tar.gz']
    >>> targets = ['est', 'nr']
    >>> filter_file_list(files, targets)
    ['est.tar.gz', 'nr.00.tar.gz']
    """
    p = re.compile('^(%s)\..*(tar.gz)$' % "|".join(targets))
    return [f for f in files if p.match(f)]


# def update_permissions(path):
#     log = logging.getLogger(__name__)
#     path = os.path.abspath(path)
#     for f in os.listdir(path):
#         try:
#             os.chmod(os.path.join(path, f), 0755)
#         except OSError:
#             sys.exit("Unable to update permissions on %s" % path)
#     log.info("File permissions for %s have been properly updated." % path)


def download(url, localfile, verbose=True):
    log = logging.getLogger(__name__)
    num_tries = 0
    max_tries = 5

    if os.path.exists(localfile):
        return True

    if verbose:
        log.info("Downloading %s" % url)

    while not os.path.exists(localfile):
        try:
            tmpd = mkdtemp()
            tmpf = "%s/%s" % (tmpd, os.path.basename(localfile))
            urllib.urlretrieve(url, tmpf)
            shutil.move(tmpf, localfile)
        except IOError:
            if num_tries > max_tries:
                raise
            num_tries += 1
            time.sleep(5)
        except Exception, e:
            log.error("NoneType when downloading %s to %s" % (url, tmpf), exc_info=True)
        finally:
            remove_dir(tmpd)
    return True


def md5sum(filename, blocksize=65536):
    hash = hashlib.md5()
    with open(filename, "r+b") as f:
        for block in iter(lambda: f.read(blocksize), ""):
            hash.update(block)
    return hash.hexdigest()


def validate_download(archive, md5file):
    if not os.path.exists(archive) or not os.path.exists(md5file):
        return False
    log = logging.getLogger(__name__)
    log.info("Validating %s using %s" % (archive, md5file))
    original = ""
    with open(md5file) as fh:
        for line in fh:
            if not original:
                try:
                    original = line.split()[0]
                except:
                    print(line)
                    raise
    current = md5sum(archive)
    return current == original


def remove_file(f):
    if f and os.path.exists(f):
        os.remove(f)


def remove_dir(d):
    if d and os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def extract_archive(archive):
    log = logging.getLogger(__name__)
    log.info("Extracting %s" % archive)
    tmpd = ""
    success = False
    try:
        tmpd = mkdtemp()
        tmpa = "%s/%s" % (tmpd, os.path.basename(archive))
        # copy to temp working dir
        shutil.copyfile(archive, tmpa)
        # extract files
        log.debug("Extracting %s to %s" % (tmpa, tmpd))
        with tarfile.open(tmpa, 'r:gz') as tar:
            tar.extractall(tmpd)
        os.remove(tmpa)
        # copy extracted files back to download dir
        for f in os.listdir(tmpd):
            src = os.path.join(tmpd, f)
            dst = os.path.join(os.path.dirname(archive), f)
            # account for inventory files
            if not os.path.exists(dst):
                shutil.move(src, dst)
        success = True
    except:
        raise
    finally:
        remove_dir(tmpd)
    return success


def process_dbfile(q):
    log = logging.getLogger(__name__)
    while True:
        f = q.get()
        #download gz
        try:
            proceed = download(f.remotetar, f.tar)
        except IOError:
            log.critical("Failed to download %s" % f.remotetar)
            remove_file(f.tar)
            proceed = False
        #download md5
        if proceed:
            try:
                proceed = download(f.remotemd5, f.md5)
            except IOError:
                log.critical("Failed to download %s" % f.md5)
                remove_file(f.md5)
                proceed = False
        # validate the download
        if proceed:
            proceed = validate_download(f.tar, f.md5)
            if not proceed:
                log.critical("Unable to validate %s using %s." % (f.tar, f.md5))
                remove_file(f.tar)
                remove_file(f.md5)
                log.info("%s and %s have been deleted." % (f.tar, f.md5))
        # extract the archive
        if proceed:
            proceed = extract_archive(f.tar)
            log.info("%s was successfully extracted." % f.tar)
        # failed
        if not proceed:
            if f.retries < 2:
                f.retries += 1
                q.put(f)
        q.task_done()


def validate_dbs(path, dbs):
    log = logging.getLogger(__name__)
    os.chdir(path)
    success = {}
    for db in dbs:
        db = os.path.join(path, db)
        if db.endswith("taxdb"):
            continue
        log.info("Validating %s" % db)
        try:
            blastdbcheck("-db", db, "-random", 10, "-verbosity", 0, "-no_isam")
            success[db] = True
        except ErrorReturnCode:
            log.critical("%s did not validate" % db)
            success[db] = False
    return success


def blastdbget(output, database, threads):
    logging.basicConfig(level=logging.INFO,
                        format="[%(asctime)s - %(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    log = logging.getLogger(__name__)

    log.info("Communicating with BLAST server")
    remote_files = file_list(BLAST_URL, BLAST_PATH)

    if not database:
        show_available(remote_files)

    if not "taxdb" in database:
        database + ("taxdb",)

    if output is None:
        output = safe_makedir(os.path.abspath('.'))
    else:
        output = safe_makedir(os.path.abspath(output))

    log.info('Using %s as working directory' % output)

    filtered_file_list = filter_file_list(remote_files, database)

    q = Queue(maxsize=0)
    for i in range(threads):
        w = Thread(target=process_dbfile, args=(q,))
        w.daemon = True
        w.start()

    log.debug("File manifest:")
    for f in filtered_file_list:
        log.debug("++++ %s" % f)
        q.put(DbFile(f, output))
    q.join()

    # validate the database
    status = validate_dbs(output, database)
    for db, success in status.iteritems():
        if success:
            log.info("%s created successfully" % db)
            # maybe delete the tgz and md5 files
        else:
            log.warn("%s failed validation" % db)
    log.info("Process complete.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('output', help='Location to store downloads and extracted blastdb')
    p.add_argument('-d', '--database', action='append',
                   help='Databases to download, eg. "-d nr". Not specifying '
                   'will list the available databases. To add multiple '
                   'databases, use this parameter multiple times.')
    p.add_argument('-t', '--threads', type=int, default=8, help='The number '
                   'of concurrent processes (downloads, extractions, etc.)')
    args = p.parse_args()
    blastdbget(args.output, args.database, args.threads)


if __name__ == '__main__':
    main()
