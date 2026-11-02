# Claude Code, Codex, and Cursor

One local stdio MCP server exposes `bulk_read` and `code_write` across these hosts.
It uses the same configurable transport as the shell scripts. Python 3.9+ is
required. No SDK installation or HTTP server is needed. Use an absolute Python
executable path if `python3` is not on the host application's PATH.

## Common setup

1. Extract Open Shunt to a permanent local directory.
2. Choose the approved provider or custom adapter in the [main README](../README.md).
3. In each template below, replace the absolute Open Shunt path, workspace directory,
   endpoint, and model IDs. The workspace must exist; relative file paths supplied
   to tools resolve inside it. Use a narrow project root, not your home directory.
4. Supply credentials through the host process environment or a company-approved
   launcher/secret manager. Never commit credentials. GUI apps may not inherit
   your terminal environment; restart them from an appropriately configured
   environment, or use an approved launcher that injects credentials then execs
   `python3 /absolute/path/to/open-shunt/scripts/shunt-mcp --workspace /absolute/project`.
   Keep launcher logs off stdout. JSON `env` settings contain non-secret defaults.

For a custom adapter, replace each template's provider settings with
`SHUNT_PROVIDER=custom`, `SHUNT_ADAPTER=/absolute/path/to/adapter`, and your reader
and writer model routes. Forward any SDK credential variables as well. For Codex,
add their **names**, not values, to `env_vars`. If changing `SHUNT_API_KEY_ENV`,
forward that selected variable rather than just the default `SHUNT_API_KEY`.

## Claude Code

**Native plugin:** use `claude --plugin-dir /absolute/path/to/open-shunt` with provider
configuration in its environment. This enables the existing skills and large-read
hooks, and calls the shell scripts. It does not require MCP setup.

**MCP alternative:** merge `claude-code.mcp.json` into `.mcp.json` in the target
project. Or, from a shell with the provider settings exported:

```bash
claude mcp add --transport stdio --scope local open-shunt -- \
  python3 /absolute/path/to/open-shunt/scripts/shunt-mcp \
  --workspace /absolute/path/to/your/project
claude mcp get open-shunt
```

Restart Claude Code, approve the project server if prompted, and inspect `/mcp`.
Choose native plugin or MCP to avoid duplicate delegation tools. MCP alone does
not install the large-read hooks. See [Claude Code's official MCP guide](https://code.claude.com/docs/en/mcp).

## Codex

Merge `codex.toml` into `~/.codex/config.toml` (or `.codex/config.toml` in a trusted
project). This template forwards `SHUNT_API_KEY` by name using `env_vars` and sets
a 240-second tool timeout, above the worker's default 180-second timeout.

```bash
codex mcp list
# In a Codex session, use /mcp to inspect active tools.
```

Restart your Codex client after editing configuration. For CLI registration,
`codex mcp add open-shunt -- python3 /absolute/path/to/open-shunt/scripts/shunt-mcp --workspace /absolute/path/to/your/project`
creates the entry; then merge the template's environment and timeout settings.
This is an MCP tool integration, not a Codex plugin/hook port. Configuration format
is documented in the [official Codex MCP guide](https://developers.openai.com/codex/mcp).

## Cursor

Merge `cursor.mcp.json` into your project's `.cursor/mcp.json`, or your personal
`~/.cursor/mcp.json`. Do not overwrite other server entries. Restart Cursor, then
inspect the server and enable its tools in MCP settings. Ensure the application
receives the credential environment described above. This is an MCP integration,
not a Cursor hook port. See [Cursor's official MCP instructions](https://prod.cursor.com/help/customization/mcp).

## Tool usage and safety

Ask the host: “Use Open Shunt's bulk_read to answer which methods access the database
in src/service.ts and src/repository.ts.” Its tool arguments are:

```json
{"question":"Which methods access the database?","paths":["src/service.ts","src/repository.ts"]}
```

For `code_write`:

```json
{"spec":"Generate tests following these conventions","reference":"tests/example.test.ts"}
```

**MCP code_write returns code for review; it never writes a target.** Have the host
review and apply output through its normal permission-controlled editing tools.
Unlike the shell script, the MCP tool deliberately has no `target` argument.
File paths are checked against the configured workspace after path resolution;
ordinary traversal and symlinks outside it are rejected. Use a trusted workspace
not concurrently mutated by untrusted processes: validate-then-open checks are
not an adversarial filesystem sandbox. This does not make untrusted model output safe,
or restrict what a trusted custom adapter can do with its process privileges.

The server processes requests sequentially and does not implement cancellation.
A host timeout/disconnect does not guarantee that an upstream request was canceled;
avoid blindly retrying requests that may still incur provider charges. Hosts may
have their own shorter tool timeouts; configure these when applicable. Files
inside the workspace can still contain secrets: choose inputs deliberately.

Only Claude Code's native plugin installs read interception. In Codex/Cursor,
ask the agent to use Open Shunt explicitly, or add a short project instruction to prefer
`bulk_read` for broad read-only questions and `code_write` for predictable drafts.
No claim is made about support in unrelated chat products or actual host-session
validation; the included tests exercise the local stdio protocol and transport.
