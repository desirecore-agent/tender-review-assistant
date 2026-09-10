# tender-review-assistant

An entry-point agent for collaborative tender review on the DesireCore platform.

## What it does

When you install this agent, it provides a guided first-use flow that:

1. Verifies the platform capabilities needed for review.
2. Installs the review team (when a real team has been published).
3. Waits for human rule approval.
4. Hands off the real request and materials to the lead reviewer.

**This agent does not perform professional tender review itself, and it does not guarantee compliance, regulatory adherence, or winning any bid.** All review conclusions are produced by the installed team members.

## Key resources

- **Entry bootstrap skill**: [`skills/tender-entry-bootstrap/README.md`](skills/tender-entry-bootstrap/README.md) — full usage guide, capability preflight, PDF smoke test, failure recovery, and data handling.
- **Chinese version**: [`skills/tender-entry-bootstrap/README.zh-CN.md`](skills/tender-entry-bootstrap/README.zh-CN.md)

## License

All original code and documentation in this agent directory are released under the [MIT License](LICENSE).

See [NOTICE](NOTICE) for third-party component acknowledgements (Python runtime, DesireCore platform, cloud model services — each under their own license).
