# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Run a named profile bundle with separate schema owners and staging directories.

import argparse
from pathlib import Path

from oratapi import __version__
from oratapi.lib.orchestration import run_bundle


def main():
    parser = argparse.ArgumentParser(description='Orchestrate an OraTAPI profile bundle.', allow_abbrev=False)
    parser.add_argument('-v', '--version', action='version', version=f'oratapi-orc {__version__}')
    parser.add_argument('--bundle', required=True, help='Named TOML bundle under ~/OraTAPI/bundles.')
    parser.add_argument('-c', '--conn_name', required=True, help='OraTAPI named connection shared by all components.')
    parser.add_argument('-To', '--table_owner', required=True, help='Source table schema, not a package owner.')
    parser.add_argument('-t', '--table_names', required=True, nargs='+', help='Source tables, or %% alone for all tables.')
    parser.add_argument('-g', '--staging_dir', type=Path,
                        help='Staging root; relative paths resolve under ~/OraTAPI. Default: ~/OraTAPI/staging.')
    parser.add_argument('--dry-run', action='store_true', help='Validate and display the plan without connecting or writing.')
    args = parser.parse_args()
    try:
        status = run_bundle(args.bundle, args.conn_name, args.table_owner, args.table_names,
                            args.staging_dir, args.dry_run)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')
    raise SystemExit(status)


if __name__ == '__main__':
    main()
