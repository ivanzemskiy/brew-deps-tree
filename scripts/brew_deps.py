#!/usr/bin/env python3

"""
brew list --installed-on-request
brew list --formula -1
brew list --cask -1

brew deps --declared <package>
brew deps --declared --include-build <package>
brew deps --declared --include-build --include-optional --include-test --include-requirements --annotate <package>

brew deps --tree --installed
"""

import argparse
import asyncio
import logging
import functools
import os
import sys
import re
import json
import multiprocessing
import pprint as _pprint

pprint = functools.partial(_pprint.pprint, width=120, sort_dicts=False)
ppformat = functools.partial(_pprint.pformat, width=120, sort_dicts=False)

TRACE = logging.NOTSET + 1
logging.addLevelName(TRACE, "TRACE")

logger = logging.getLogger("brew_deps")
logger.setLevel(TRACE)

handler = logging.FileHandler(f"brew_deps.log", mode="w")
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)

sem = asyncio.Semaphore(multiprocessing.cpu_count())
pattern_dep = re.compile(r"^(.+?)(?= \[|$)")
pattern_ann = re.compile(r"(?: \[(\w+)])")


def parse_dep(acc: dict, s: str):
    dep = pattern_dep.match(s).group()
    annotaions = pattern_ann.findall(s) or ["runtime"]
    for a in annotaions:
        acc.setdefault(a, []).append(dep)
    return acc


# parse_dep("curl [build] [test] [implicit]", dict())
# parse_dep(":Xcode >= 14.2 (on macOS) [build]", dict())
# parse_dep(":macOS", dict())


async def run(cmd: str) -> str:
    async with sem:
        logger.debug(">>> %s", cmd)
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode().splitlines()


async def process_brew(installed):
    if not installed:
        installed = await run("brew list --installed-on-request")
    logger.debug(installed)
    formulas, casks = await asyncio.gather(
        run("brew list --formula -1"),
        run("brew list --cask -1"),
    )
    logger.debug(formulas)
    logger.debug(casks)

    def brew_deps(f):
        return run(
            "brew deps --declared "
            "--include-build --include-optional --include-test "
            "--include-requirements --annotate " + f
        )

    result_f, result_c = await asyncio.gather(
        asyncio.gather(*[brew_deps(f"--formula {f}") for f in formulas]),
        asyncio.gather(*[brew_deps(f"--cask {f}") for f in casks]),
    )
    logger.debug(result_f)
    logger.debug(result_c)

    result_f = dict(
        zip(
            formulas,
            map(lambda lines: functools.reduce(parse_dep, lines, dict()), result_f),
        )
    )
    result_c = dict(
        zip(
            casks,
            map(lambda lines: functools.reduce(parse_dep, lines, dict()), result_c),
        )
    )
    logger.info(ppformat(result_f))
    logger.info(ppformat(result_c))

    with open("brew-flat.json", "w") as f:
        # json.dump(result_f, f, indent=2)
        print(ppformat(result_f).replace("'", '"'), file=f)

    def traverse_dict(src: dict, dst: dict, callback):
        for k, v in src.items():
            if isinstance(v, dict):
                traverse_dict(v, dst[k], callback)
            elif isinstance(v, list):
                for i, e in enumerate(v):
                    dst[k][i] = callback(e)
            else:
                dst[k] = callback(v)
        return dst

    def mapper(v):
        return {v: result_f[v]} if v in result_f and result_f[v] else v

    tree_f = traverse_dict(result_f, result_f.copy(), mapper)
    tree_c = traverse_dict(result_c, result_c.copy(), mapper)
    logger.info("")
    logger.info(ppformat(tree_f))
    logger.info(ppformat(tree_c))

    with open("brew-tree.json", "w") as f:
        # json.dump(tree_f, f, indent=2)
        print(ppformat(tree_f, width=125).replace("'", '"'), file=f)


# loop = asyncio.get_running_loop()
# with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
#     await loop.run_in_executor(pool, blocking_io)


def main():
    parser = argparse.ArgumentParser(
        description="brew dependencies tree",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--target", help="output directory")
    group.add_argument("-v", "--verbose", action="store_true")
    group.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("formula", nargs="*", help="for specific formula(s)")
    args = parser.parse_args()

    logger.log(TRACE, args)

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.ERROR)

    if args.target:
        os.chdir(args.target)
    if args.formula:
        import warnings

        warnings.warn(
            f"selective list {args.formula} ignored, currently only the whole list of formulas is supported",
            UserWarning,
            stacklevel=2,
        )

    asyncio.run(process_brew(args.formula))


if __name__ == "__main__":
    main()
