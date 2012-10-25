"""Utility functions for fabric tasks"""
from __future__ import print_function

from fabric.api import (env, get, hide, hosts, lcd, local, put, roles,
                        run, runs_once, settings, sudo)
from StringIO import StringIO
from contextlib import contextmanager
from fabric.colors import green
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project
from os.path import dirname, join
import os
import re
import time

### {{{ ROLES HELPERS


def default_roles(*role_list):
    """Decorate task with these roles by default, but override with -R, -H"""
    def selectively_attach(func):
        """Only decorate if nothing specified on command line"""
        # pylint: disable=W0142
        if not env.roles and not env.hosts:
            return roles(*role_list)(func)
        else:
            if env.hosts:
                func = hosts(*env.hosts)(func)
            if env.roles:
                func = roles(*env.roles)(func)
            return func
    return selectively_attach


### ROLES HELPERS }}}
### {{{ FILE AND DIRECTORY HELPERS


def chown(dirs, user=None, group=None):
    """User sudo to set user and group ownership"""
    if isinstance(dirs, basestring):
        dirs = [dirs]
    args = ' '.join(dirs)
    if user and group:
        return sudo('chown {}:{} {}'.format(user, group, args))
    elif user:
        return sudo('chown {} {}'.format(user, args))
    elif group:
        return sudo('chgrp {} {}'.format(group, args))
    else:
        return None


def chput(local_path=None, remote_path=None, user=None, group=None,
          mode=None, use_sudo=True, mirror_local_mode=False, check=True):
    """Put file and set user and group ownership.  Default to use sudo."""
    # pylint: disable=R0913
    if env.get('full') or not check or diff(local_path, remote_path):
        result = put(local_path, remote_path, use_sudo,
                     mirror_local_mode, mode)
        with hide('commands'):
            chown(remote_path, user, group)
        return result
    else:
        return None


def cron(name, timespec, user, command, environ=None, disable=False):
    """Create entry in /etc/cron.d"""
    path = '/etc/cron.d/{}'.format(name)
    if disable:
        sudo('rm ' + path)
        return
    entry = '{}\t{}\t{}\n'.format(timespec, user, command)
    if environ:
        envstr = '\n'.join('{}={}'.format(k, v)
                           for k, v in environ.iteritems())
        entry = '{}\n{}'.format(envstr, entry)
    chput(StringIO(entry), path, use_sudo=True,
          mode=0o644, user='root', group='root')


def diff(local_path, remote_path):
    """Return true if local and remote paths differ in contents"""
    with hide('commands'):
        if isinstance(local_path, basestring):
            local_content = local("cat '{}'".format(local_path), capture=True)
        else:
            pos = local_path.tell()
            local_content = local_path.read()
            local_path.seek(pos)
        remote_content = StringIO()
        with settings(hide('warnings'), warn_only=True):
            if get(remote_path, remote_content).failed:
                return True
        return local_content.strip() != remote_content.getvalue().strip()


def md5sum(filename, use_sudo=False):
    """Return md5sum of remote file"""
    runner = sudo if use_sudo else run
    with hide('commands'):
        return runner("md5sum '{}'".format(filename)).split()[0]


def mkdir(dirs, user=None, group=None, mode=None, use_sudo=True):
    """Create directory with sudo and octal mode, then set ownership."""
    if isinstance(dirs, basestring):
        dirs = [dirs]
    if not env.get('full'):
        dirs = [d for d in dirs if not exists(d)]
    runner = sudo if use_sudo else run
    if dirs:
        modearg = '-m {:o}'.format(mode) if mode else ''
        cmd = 'mkdir -v -p {} {}'.format(modearg, ' '.join(dirs))
        result = runner(cmd)
        with hide('commands'):
            chown(dirs, user, group)
        return result
    else:
        return None


def rsync(local_path, remote_path, exclude=None, extra_opts=None):
    """Helper to rsync submodules across"""
    if not local_path.endswith('/'):
        local_path += '/'
    exclude = exclude or []
    exclude.extend(['*.egg-info', '*.pyc', '.git', '.gitignore',
                    '.gitmodules', '/build/', '/dist/'])
    with hide('running'):
        run("mkdir -p '{}'".format(remote_path))
        return rsync_project(
            remote_path, local_path, delete=True,
            extra_opts='-i --omit-dir-times -FF ' +
                       (extra_opts if extra_opts else ''),
            ssh_opts='-o StrictHostKeyChecking=no',
            exclude=exclude)


@contextmanager
def tempput(local_path=None, remote_path=None, use_sudo=False,
            mirror_local_mode=False, mode=None):
    """Put a file to remote and remove it afterwards"""
    import warnings
    warnings.simplefilter('ignore', RuntimeWarning)
    if remote_path is None:
        remote_path = os.tempnam()
    put(local_path, remote_path, use_sudo, mirror_local_mode, mode)
    yield remote_path
    run("rm '{}'".format(remote_path))


@contextmanager
def watch(filenames, callback, use_sudo=False):
    """Call callback if any of filenames change during the context"""
    filenames = [filenames] if isinstance(filenames, basestring) else filenames
    old_md5 = {fn: md5sum(fn, use_sudo) for fn in filenames}
    yield
    for filename in filenames:
        if md5sum(filename, use_sudo) != old_md5[filename]:
            callback()
            return

### FILE AND DIRECTORY HELPERS }}}
### {{{ DEBIAN/UBUNTU HELPERS


def debconf_set_selections(package, selections):
    """Given package and map config:(type,value), set selections"""
    text = '\n'.join(' '.join([package, k, t, v]) for
                     k, (t, v) in selections.iteritems())
    sudo('debconf-set-selections <<-HEREDOC\n{}\nHEREDOC'.format(text))


def install_deb(pkgname, url):
    """Install package from custom deb hosted on S3.
    Return true if package was installed by this invocation."""
    status = run("dpkg-query -W -f='${Status}' %s ; true" % pkgname)
    if ('installed' not in status) or ('not-installed' in status):
        deb = url.rpartition('/')[2]
        debtmp = join('/tmp', deb)
        run("wget --no-check-certificate -qc -O '{}' '{}'".format(debtmp, url))
        sudo("dpkg -i '{0}' && rm -f '{0}'".format(debtmp))
        return True
    else:
        return False


def package_ensure_apt(*packages):
    """Ensure apt packages are installed"""
    package = " ".join(packages)
    status = run("dpkg-query -W -f='${Status} ' {p} ; true".format(p=package))
    if 'No packages found' in status or 'not-installed' in status:
        sudo("apt-get --yes install " + " ".join(package))
        return False
    else:
        return True


@runs_once
def update_apt(days=14, upgrade=False):
    """Update apt index if not update in last N days"""
    # Check the apt-get update timestamp (works on Ubuntu only)
    with hide('commands'):
        last_update = float(run(
            "stat -c %Y /var/lib/apt/periodic/update-success-stamp"))
    if (time.time() - last_update) > days * 86400:
        sudo("apt-get --yes update")
        if upgrade:
            sudo("apt-get --yes upgrade")

### DEBIAN/UBUNTU HELPERS }}}
### {{{ VERSION TAGGING HELPERS


def make_version(ref=None):
    """Build git version string for current directory"""
    cmd = 'git describe --tags --abbrev=6 {}'.format(ref or '')
    with hide('commands'):
        version = local(cmd, capture=True).strip()
    if re.match('^v[0-9]', version):
        version = version[1:]
    # replacements to match semver.org build numbers
    if '-' in version:
        head, _, tail = version.partition('-')
        count, _, sha = tail.partition('-g')
        version = head + '+' + count + '-' + sha
    return version


def rsync_git(local_path, remote_path, exclude=None, extra_opts=None,
              version_file='version.txt'):
    """Rsync deploy a git repo.  Write and compare version.txt"""
    with settings(hide('output', 'running'), warn_only=True):
        print(green('Version On Server: ' + run('cat ' + join(
              remote_path, version_file)).strip()))
    print(green('Now Deploying Version ' +
          write_version(join(local_path, version_file))))
    rsync(local_path, remote_path, exclude, extra_opts)


def tagversion(repo, level='patch', special=''):
    """Increment and return tagged version in git.
    Increment levels are patch, minor and major.

    Using semver.org versioning: {major}.{minor}.{patch}{special}
    Special must start with a-z and consist of _a-zA-Z0-9.
    """
    prepend = 'v'
    with lcd(repo):
        oldversion = local(
            'git describe --abbrev=0 --tags', capture=True).strip()
        if oldversion.startswith('v'):
            oldversion = oldversion[1:]
        else:
            prepend = ''
    major, minor, patch = [int(x) for x in re.split('\D', oldversion, 3)[:3]]
    if special:
        if not re.match('^[a-z]', special):
            raise ValueError('Special must start with a-z')
        if not re.match('[_a-zA-Z0-9]+', special):
            raise ValueError('Must contain start with lowercase letter')
    if level == 'major':
        major, minor, patch = major + 1, 0, 0
    elif level == 'minor':
        major, minor, patch = major, minor + 1, 0
    elif level == 'patch':
        major, minor, patch = major, minor, patch + 1
    version_string = '{}.{}.{}'.format(major, minor, patch) + special
    with lcd(repo):
        local('git tag -s --force {}{}'.format(prepend, version_string))
    return version_string


def write_version(path, ref=None):
    """Update version file using git desribe"""
    with lcd(dirname(path)):
        version = make_version(ref)
    if (env.get('full') or not os.path.exists(path)
            or version != open(path).read().strip()):
        with open(path, 'w') as out:
            out.write(version + '\n')
    return version

### VERSION TAGGING HELPERS }}}
### {{{ SPLUNK HELPERS


def splunk(cmd, user='admin', passwd='changeme'):
    """Authenticated call to splunk"""
    return sudo('/opt/splunkforwarder/bin/splunk {} -auth {}:{}'
                .format(cmd, user, passwd))


def splunk_monitor(monitors):
    """Monitor a list of (path, sourcetype) pairs in splunk"""
    if not exists('/opt/splunkforwarder'):
        return
    if not env.get('splunk_monitors'):
        with hide('commands'):
            env['splunk_monitors'] = str(splunk('list monitor'))
    for path, sourcetype in monitors:
        if path not in env['splunk_monitors']:
            with hide('everything'):
                run("touch '{}'; true".format(path))
            splunk("add monitor '{}' -sourcetype {}".format(path, sourcetype))
            env['splunk_monitors'] += '\n' + path

# SPLUNK HELPERS }}}
# vim:foldnestmax=1:foldenable:foldmethod=marker:
