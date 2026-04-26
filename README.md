# ghafi

GitHub CLI and agent — an AgentCulture manager.

`ghafi` bootstraps and maintains AgentCulture sibling repositories on GitHub:
create new repos with workflow permissions, scaffold the afi-cli python-cli
template into them, and create the `pypi` / `testpypi` GitHub Environments
needed for Trusted Publishing.

## Install

```bash
uv tool install ghafi
# or
pip install ghafi
```

## Usage

```bash
export GITHUB_TOKEN=ghp_...

ghafi learn                          # self-teaching prompt (also --json)
ghafi whoami                         # verify the token
ghafi repo create my-new-repo        # dry-run: prints would-be POST body
ghafi repo create my-new-repo --apply
ghafi repo scaffold ./my-new-repo --apply       # shells out to `afi cli cite`
ghafi repo env my-new-repo --name pypi --apply
ghafi repo env my-new-repo --name testpypi --apply
```

Every GitHub-mutating verb defaults to **dry-run**. Pass `--apply` to commit.

## Status

Early v0.x. See `CHANGELOG.md` for the full surface and `CLAUDE.md` for the
project shape and conventions.

## License

MIT.
