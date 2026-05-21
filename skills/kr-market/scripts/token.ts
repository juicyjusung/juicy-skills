#!/usr/bin/env bun
import { getToken, revokeToken } from "./_client.ts";

const args = process.argv.slice(2);
const cmd = args[0] ?? "show";

try {
  if (cmd === "--refresh" || cmd === "refresh") {
    const t = await getToken(true);
    console.log(JSON.stringify({ refreshed: true, token_preview: t.slice(0, 12) + "..." }));
  } else if (cmd === "--revoke" || cmd === "revoke") {
    await revokeToken();
    console.log(JSON.stringify({ revoked: true }));
  } else {
    const t = await getToken();
    console.log(JSON.stringify({ token_preview: t.slice(0, 12) + "...", cached: true }));
  }
} catch (e) {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
}
