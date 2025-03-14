# sotawhat

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

This is a repo for arxiv paper searching with keywords, **modified from sotawhat, which is apperent.**

Up to now I only slightly modify the code for a few functions:
- modified the link session so that the links to the arxiv papers are properly shown in cmd;
- disable the filering algorithm so that the whole abstract, instead of sentences with keywords, are shown in cmd;
- Keywords are scanned in abstracts and titles;
- Add sorting algorithm to arrange the papers in a timeline (the higher, the later)


**Thanks again for the origin code from sotawhat!**

# Usage

Step 1: clone this repo, and go inside that repo:
```bash
$ git clone [HTTPS or SSH linnk to this repo]
$ cd sotawhat
```
Step 2: install using pip

```bash
$ pip3 install .
```

On Windows, due to encoding errors, the script may cause issues when run on the command line. It is
recommended to use `pip install win-unicode-console --upgrade` prior to launching the script. If you get
UnicodeEncodingError, you *must* install the above.

On Mac, it works fine.

Step 3: one-line command

```bash
$ scan KEY_WORD TIMES
```

for example: `scan reasoning model 20`