## Terminal command execution

for output directly. Use this pattern instead for ALL terminal commands:

1. Run with `isBackground: true` and pipe output through `tee` to both the terminal and a temp file:
   `<command> 2>&1 | tee .idea/.copilot_out.txt`
2. Immediately call `read_file` on `.idea/.copilot_out.txt` to get the output.
3. For exit-code checking, append `; echo "EXIT:$pipestatus[1]"` before the redirect.

Example:

```
uv run ls -l 2>&1 | tee .idea/.copilot_out.txt ; echo "EXIT:$pipestatus[1]" >> .idea/.copilot_out.txt
```

Then read `.idea/.copilot_out.txt`.

Never use `isBackground: false` for commands that produce output.
Never use `get_terminal_output` — it returns null in this environment.
