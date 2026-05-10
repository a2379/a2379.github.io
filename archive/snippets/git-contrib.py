#!/usr/bin/env python3
"""Collect git repos in CWD and summarize an author's contributions.

This script makes some assumptions and is brittle.
Feel free to edit. It is available under the MIT License.
"""

import argparse
from pathlib import Path
import subprocess
import os
from datetime import datetime
import json


def _get_lang():
    out = subprocess.check_output(["cloc", "--json", "."], text=True)
    data = json.loads(out)
    for lang, stats in data.items():
        if not isinstance(stats, dict) or "code" not in stats:
            continue
        # First lang is the one we want
        return lang
    return "???"


def _collect_stats(authors):
    ns = subprocess.check_output(
        ["git", "log", "--pretty=tformat:", "--numstat"] + authors,
        text=True).strip()

    added = 0
    deleted = 0
    commits = 0
    for line in ns.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, _ = parts
        commits += 1
        added += int(a)
        deleted += int(d)
    return added, deleted, commits


def _collect_data(cwd, names, use_cwd):
    data = {}
    totals = {"added": 0, "deleted": 0, "commits": 0}
    authors = [f"--author={x}" for x in names]

    if use_cwd:
        subdirs = [Path(cwd)]
    else:
        subdirs = Path(cwd).iterdir()
    pwd = os.getcwd()
    for subdir in subdirs:
        print(f"Collecting stats for {subdir}")
        if not subdir.is_dir():
            continue
        os.chdir(subdir)
        name = subdir.name
        remote = subprocess.check_output(["git", "remote", "get-url", "origin"],
                                         text=True).strip()
        info = subprocess.check_output(
            ["git", "log", "--date=short", "--stat", "--pretty=format:commit %h %s / %ad"] + authors,
            text=True).strip()
        lang = _get_lang()

        data[name] = {"remote": remote, "info": info, "lang": lang}
        a, d, c = _collect_stats(authors)
        totals["added"] += a
        totals["deleted"] += d
        totals["commits"] += c

        os.chdir(pwd)

    return data, totals


def _write_html_report(data, totals, loc, no_date):
    with open("report.html", "w") as f:

        if not no_date:
            f.write('<p>Report generated on {} using <a href="https://antr.me/archive/snippets/git-contrib.py">git-contrib.py</a></p>\n'.format(
                datetime.now().strftime("%Y-%m-%d")))

        f.write("<h3>Total</h3>\n")
        f.write("<p>Commits: {:,}<br>Lines added: {:,}<br>Lines removed: {:,}</p>".format(
            totals["commits"],
            totals["added"],
            totals["deleted"]))

        for key, val in data.items():
            if key == "_totals":
                continue
            remote = val["remote"]
            info = val["info"]
            f.write("<h3>{}</h3>\n".format(key))
            f.write('<p><a href="{}">{}</a><br>Language: {}</p>\n'.format(
                remote, remote, val["lang"]))
            f.write('<pre>{}</pre>'.format(info))


def _get_args():
    parser = argparse.ArgumentParser(description="Generate an HTML report for Git repos.")
    parser.add_argument(
        "-d", "--cwd", default=".", type=str,
        help="directory to scan for repos (default is current directory)")
    parser.add_argument(
        "-i", "--include", action='append', default=[], type=str,
        help="extra repo directories (may be specified multiple times)")
    parser.add_argument(
        "-a", "--names", action='append', required=True, type=str,
        help="""author name or email to filter commits by.
May be specified multiple times""")
    parser.add_argument(
        "-p", "--pops", action='append', type=str,
        help="""repo names to move to the back of the sorted list.
May be specified multiple times.""")
    parser.add_argument(
        "-o", "--outfile", default="report.html", type=str,
        help="output HTML report location (default is report.html)")
    parser.add_argument(
        "-n", "--no-date", action="store_true",
        help="Suppress the generated date in the report")
    return parser.parse_args()


def main():
    args = _get_args()
    d, t = _collect_data(args.cwd, args.names, False)
    for x in args.include:
        d1, t1 = _collect_data(x, args.names, True)
        d.update(d1)
        t["added"] += t1["added"]
        t["deleted"] += t1["deleted"]
        t["commits"] += t1["commits"]
    d = dict(sorted(d.items()))
    for p in args.pops:
        d[p] = d.pop(p)
    _write_html_report(d, t, args.outfile, args.no_date)
    print(f"Report written to {args.outfile}")


if __name__ == "__main__":
    main()
