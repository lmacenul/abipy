#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import argparse

from abipy.flowtk.psrepos import ALL_REPOS, PseudosRepo, pprint_repos, repos_from_id_list


def user_wants_to_abort():
    """Interactive problem, return False if user entered `n` or `no`."""
    try:
        answer = input("\nDo you want to continue [Y/n]")
    except EOFError:
        return False

    return answer.lower().strip() in ["n", "no"]


def get_repos_root(options) -> str:
    """
    Return the path to the PseudoDojo installation directory.
    Create the directory if needed.
    """
    repos_root = options.repos_root
    if not os.path.exists(repos_root):
        os.mkdir(repos_root)

    return repos_root


def abips_list(options):
    """
    List all installed pseudopotential repos.
    """
    repos_root = get_repos_root(options)
    dirpaths = [os.path.join(repos_root, name) for name in os.listdir(repos_root) if
                os.path.isdir(os.path.join(repos_root, name))]

    if not dirpaths:
        print("Could not find any pseudopotential repository installed in:", repos_root)
        return 0

    print(f"The following pseudopotential repositories are installed in {repos_root}:\n")
    repos = [PseudosRepo.from_dirpath(dirpath) for dirpath in dirpaths]
    # Keep the list sorted by ID.
    repos = sorted(repos, key=lambda repo: repo.rid)
    pprint_repos(repos, repos_root=repos_root)

    if options.verbose:
        for repo in repos:
            if repo.ispaw: continue
            pseudos = repo.get_pseudos(repos_root, table_accuracy="standard")
            print(pseudos)
    else:
        print("\nUse -v to print the pseudos")

    if not options.checksums:
        return 0

    exc_list = []
    for repo in repos:
        try:
            repo.validate_checksums(repos_root, options.verbose)
        except Exception as exc:
            exc_list.append(exc)

    if exc_list:
        print("\nList of exceptions raised by validate_checksums:")
        for exc in exc_list:
            print(exc)

    return len(exc_list)


def abips_avail(options):
    """
    Show available repos.
    """
    print("List of available pseudopotential repositories:\n")
    repos_root = get_repos_root(options)
    pprint_repos(ALL_REPOS, repos_root)


def abips_nc_get(options):
    """
    Get NC repo. Can choose among three formats: psp8, upf2 and psml.
    By default we fetch all formats.
    """
    repos_root = get_repos_root(options)
    repos = [repo for repo in ALL_REPOS if repo.isnc and not repo.is_installed(repos_root)]
    if not repos:
        print(f"All registered NC repositories are already installed in {repos_root}. Returning")
        return 0

    print("The following NC repositories will be installed:\n")
    pprint_repos(repos, repos_root=repos_root)
    if not options.yes and user_wants_to_abort(): return 2

    print("Fetching NC repositories. It may take some time ...")
    for repo in repos:
        repo.install(repos_root, options.verbose)

    abips_list(options)
    return 0


def abips_paw_get(options):
    """
    Get PAW repositories in PAWXML format.
    """
    repos_root = get_repos_root(options)
    repos = [repo for repo in ALL_REPOS if repo.ispaw and not repo.is_installed(repos_root)]
    if not repos:
        print(f"All registered PAW repositories are already installed in {repos_root}. Returning")
        return 0

    print("The following PAW repositories will be installed:")
    pprint_repos(repos, repos_root=repos_root)
    if not options.yes and user_wants_to_abort(): return 2

    print("Fetching PAW repositories. It may take some time ...")
    for repo in repos:
        repo.install(repos_root, options.verbose)

    abips_list(options)
    return 0


def abips_get_byid(options):
    """
    Get list of repos by their IDs.
    Use the `avail` command to get the repo ID.
    """
    repos_root = get_repos_root(options)
    repos = repos_from_id_list(options.id_list)
    repos = [repo for repo in repos if not repo.is_installed(repos_root)]

    if not repos:
        print("Tables are already installed!")
        abips_list(options)
        return 1

    print("The following pseudopotential repositories will be installed:")
    pprint_repos(repos, repos_root=repos_root)
    if not options.yes and user_wants_to_abort(): return 2

    for repo in repos:
        repo.install(repos_root, options.verbose)

    abips_list(options)
    return 0


def abips_show(options):
    """Show Pseudopotential tables"""

    repos_root = get_repos_root(options)
    repos = repos_from_id_list(options.id_list)
    repos = [repo for repo in repos if not repo.is_installed(repos_root)]

    if not repos:
        print("Tables are already installed!")
        abips_list(options)
        return 1

    for repo in repos:
        print(repo)
        pseudos = repo.get_pseudos(repos_root, table_accuracy="standard")
        print(pseudos)

    return 0


def get_epilog():
    return """\

Usage example:

  abips.py avail                          --> Show registered repositories and the associated IDs.
  abips.py list                           --> List installed repositories.
  abips.py get_byid 1 3                   --> Download repositories by ID(s).          
  abips.py nc_get                         --> Get all NC repositories (most recent version)
  abips.py nc_get -xc PBE -fr -sr --version 0.4 
  abips.py paw_get                        --> Get all PAW repositories (most recent version)
"""


def get_parser(with_epilog=False):

    # Parent parser for common options.
    copts_parser = argparse.ArgumentParser(add_help=False)
    copts_parser.add_argument('-v', '--verbose', default=0, action='count', # -vv --> verbose=2
                              help='verbose, can be supplied multiple times to increase verbosity.')

    copts_parser.add_argument('--repos-root', "-r", type=str,
                              default=os.path.expanduser(os.path.join("~", ".abinit", "pseudos")),
                              help='Installation directory. Default: $HOME/.abinit/pseudos')

    copts_parser.add_argument('-y', "--yes", action="store_true", default=False,
                              help="Do not ask for confirmation when installing repositories.")

    copts_parser.add_argument("-c", "--checksums", action="store_true", default=False,
                              help="Validate checksums")

    # Build the main parser.
    parser = argparse.ArgumentParser(epilog=get_epilog() if with_epilog else "",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-V', '--version', action='version')  #, version=__version__)

    # Create the parsers for the sub-commands
    subparsers = parser.add_subparsers(dest='command', help='sub-command help', description="Valid subcommands")

    # Subparser for list command.
    p_list = subparsers.add_parser("list", parents=[copts_parser], help=abips_list.__doc__)

    # Subparser for avail command.
    subparsers.add_parser("avail", parents=[copts_parser], help=abips_avail.__doc__)

    # Subparser for nc_get command.
    p_nc_get = subparsers.add_parser("nc_get", parents=[copts_parser], help=abips_nc_get.__doc__)

    # Subparser for paw_get command.
    p_paw_get = subparsers.add_parser("paw_get", parents=[copts_parser], help=abips_paw_get.__doc__)

    # Subparser for get_byid command.
    p_get_byid = subparsers.add_parser("get_byid", parents=[copts_parser], help=abips_get_byid.__doc__)
    p_get_byid.add_argument("id_list", type=int, nargs="+", help="List of PseudoPotential Repo IDs to download.")

    # Subparser for show command.
    p_show = subparsers.add_parser("show", parents=[copts_parser], help=abips_show.__doc__)
    p_show.add_argument("id_list", type=int, nargs="+", help="List of PseudoPotential Repo IDs to download.")

    return parser


def main():

    def show_examples_and_exit(err_msg=None, error_code=1):
        """Display the usage of the script."""
        sys.stderr.write(get_epilog())
        if err_msg: sys.stderr.write("Fatal Error\n" + err_msg + "\n")
        sys.exit(error_code)

    parser = get_parser(with_epilog=True)

    # Parse command line.
    try:
        options = parser.parse_args()
    except Exception as exc:
        show_examples_and_exit(error_code=1)

    return globals()[f"abips_{options.command}"](options)


if __name__ == "__main__":
    sys.exit(main())