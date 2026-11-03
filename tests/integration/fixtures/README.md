# Offline pipeline inputs

`poll-plan.json` is a version-1 synthetic fetch-result plan. Its Base64 bodies are exact copies of the hand-authored shared `rss-basic.xml` and `atom-basic.xml` fixtures; integration tests check equality. They are not downloaded articles or publisher material. All hosts are reserved and source records remain disabled.

Use `tests/fixtures/views/empty.json` as prior state, explicit `web/styles.css` as the reviewed stylesheet, and a claimed 40-hex code reference. Runtime collection envelopes stay private/untracked and outside candidate output. The plan carries no file reference or URL to fetch.
