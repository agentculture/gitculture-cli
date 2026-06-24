# ghafi → gitculture-cli

`ghafi` has been renamed to **`gitculture-cli`**.

This PyPI package (`ghafi`) is now a **compatibility shim**: it contains no code
of its own and simply depends on
[`gitculture-cli`](https://pypi.org/project/gitculture-cli/). Installing it pulls
in the real tool, which provides **both** the new `gitculture` command and the
old `ghafi` command (kept as a backward-compatible alias).

```bash
pip install ghafi            # still works — pulls in gitculture-cli
pip install gitculture-cli   # preferred going forward

gitculture --version         # primary command
ghafi --version              # alias — same CLI
```

Source, issues, and releases live in the original repository:
<https://github.com/agentculture/ghafi>.
