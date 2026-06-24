# gitculture-cli

GitHub CLI and agent — an AgentCulture manager.

`gitculture` bootstraps and maintains AgentCulture sibling repositories on GitHub:
create new repos with workflow permissions, scaffold the afi-cli python-cli
template into them, and create the `pypi` / `testpypi` GitHub Environments
needed for Trusted Publishing.

## Install

```bash
uv tool install gitculture-cli
# or
pip install gitculture-cli
```

The package was formerly published as `ghafi`; `pip install ghafi` still works
as a compatibility shim.

## Usage

```bash
export GITHUB_TOKEN=ghp_...

gitculture learn                          # self-teaching prompt (also --json)
gitculture whoami                         # verify the token
gitculture repo create my-new-repo        # dry-run: prints would-be POST body
gitculture repo create my-new-repo --apply
gitculture repo scaffold ./my-new-repo --apply       # shells out to `afi cli cite`
gitculture repo env my-new-repo --name pypi --apply
gitculture repo env my-new-repo --name testpypi --apply
```

The `ghafi` command remains as a backward-compatible alias.

Every GitHub-mutating verb defaults to **dry-run**. Pass `--apply` to commit.

## Status

Early v0.x. See `CHANGELOG.md` for the full surface and `CLAUDE.md` for the
project shape and conventions.

## License

MIT.
