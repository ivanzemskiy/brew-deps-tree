## Brew maintenance

### Cleanup problem

It's unclear which formulas are added only as build dependencies. As a result, it's difficult to understand which dependencies can be removed (saving disk space) without damaging other formulas.

```
brew list --installed-on-request
brew leaves --installed-as-dependency
brew deps --tree --installed
```

The `--annotate` flag does not work with `--tree`.

### Helper script

Can help if you want to remove formulas / casks, but fair to break other formulas.

```
% ./scripts/brew_deps.py -h
usage: brew_deps.py [-h] [-t TARGET | -v | -q] [formula ...]
```

produces `brew-tree.json` which includes all the `build`/`runtime`/`test` ... dependencies

can be quickly checked using `jg` or a similar tool
