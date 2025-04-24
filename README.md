# **Instructions**

## Environment

### Creating an environment

```sh
$ conda create -y --prefix ./feature_env
```

### Running your environment

```sh
$ conda activate ./feature_env
```

```sh
$ conda install python=3.7
$ which python
$ alias py37="{PATH-OUTPUTTED-FROM-ABOVE}"
```

### Dependencies

```sh
$ conda install pip
```

```sh
$ pip install requests
$ pip install tabulate
$ pip install pyyaml
```

## Request the Feature-Tracker Dashboard

```sh
$ py37 featureTracker.py {INTERVAL=week|month} {DATE-START} {DATE-END} {FEATURE-PAGE-PATH} "{FEATURE+CODE}" "{COMPARISON+FEATURE+CODE+1}" "{COMPARISON+FEATURE+CODE+N}"
```

### Example - comparison features are optional:

```sh
$ py37 featureTracker.py week 2025-03-30 2025-04-19 "/" "Feature+1" "Comparison+Feature+2" "Comparison+Feature+n"
```

### Shutting down environment

```sh
$ conda deactivate
```
