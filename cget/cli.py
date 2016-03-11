import click, os, functools

from cget import __version__
from cget.prefix import CGetPrefix
import cget.util as util


aliases = {
    'rm': 'remove'
}

class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        return click.Group.get_command(self, ctx, aliases[cmd_name])


@click.group(cls=AliasedGroup, context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=__version__, prog_name='cget')
def cli():
    pass

def use_prefix(f):
    @click.option('-p', '--prefix', envvar='CGET_PREFIX', help='Set prefix used to install packages')
    @click.option('-v', '--verbose', is_flag=True, envvar='VERBOSE', help="Enable verbose mode")
    @functools.wraps(f)
    def w(prefix, verbose, *args, **kwargs):
        if prefix is None: prefix = os.path.join(os.getcwd(), 'cget')
        f(CGetPrefix(prefix, verbose), *args, **kwargs)
    return w

@cli.command(name='init')
@use_prefix
@click.option('-t', '--toolchain', required=False, help="Set cmake toolchain file to use")
@click.option('--cxxflags', required=False, help="Set additional c++ flags")
@click.option('--ldflags', required=False, help="Set additional linker flags")
@click.option('--std', required=False, help="Set C++ standard if available")
def init_command(prefix, toolchain, cxxflags, ldflags, std):
    """ Initialize install directory """
    prefix.write_cmake(always_write=True, toolchain=os.path.abspath(toolchain), cxxflags=cxxflags, ldflags=ldflags, std=std)

@cli.command(name='install')
@use_prefix
@click.option('-t', '--test', is_flag=True, help="Test package before installing by running the test or check target")
@click.option('-f', '--file', default=None, help="Install packages listed in the file")
@click.argument('pkgs', nargs=-1)
def install_command(prefix, pkgs, file, test):
    """ Install packages """
    for pkg in list(pkgs)+prefix.from_file(file):
        try:
            click.echo(prefix.install(pkg, test=test))
        except:
            click.echo("Failed to build package {0}".format(pkg))
            prefix.remove(pkg)
            if prefix.verbose: raise

@cli.command(name='remove')
@use_prefix
@click.argument('pkgs', nargs=-1)
@click.option('-y', '--yes', is_flag=True, default=False)
def remove_command(prefix, pkgs, yes):
    """ Remove packages """
    pkgs_set = set((dep.name for pkg in pkgs for dep in prefix.list(pkg, recursive=True)))
    click.echo("The following packages will be deleted:")
    for pkg in pkgs_set: click.echo(pkg)
    if not yes: yes = click.confirm("Are you sure you want to remove these packages?")
    if yes:
        for pkg in pkgs_set:
            try:
                prefix.remove(pkg)
                click.echo("Removed package {0}".format(pkg))
            except:
                click.echo("Failed to remove package {0}".format(pkg))
                if prefix.verbose: raise

@cli.command(name='list')
@use_prefix
def list_command(prefix):
    """ List installed packages """
    for pkg in prefix.list():
        click.echo(pkg.name)

# TODO: Make this command hidden
@cli.command(name='size')
@use_prefix
@click.argument('n')
def size_command(prefix, n):
    pkgs = len(list(util.ls(prefix.get_package_directory(), os.path.isdir)))
    deps = len(list(util.ls(prefix.get_deps_directory(), os.path.isdir)))
    if deps > pkgs:
        raise util.BuildError("Extra deps items: {0}".format(deps))
    if pkgs != int(n):
        raise util.BuildError("Not the correct number of items: {0}".format(pkgs))

@cli.command(name='clean')
@use_prefix
def clean_command(prefix):
    """ Clear directory """
    prefix.clean()

@cli.command(name='pkg-config', context_settings=dict(
    ignore_unknown_options=True,
))
@use_prefix
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def pkg_config_command(prefix, args):
    """ Pkg config """
    prefix.pkg_config(args)


if __name__ == '__main__':
    cli()

