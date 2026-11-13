# QoL Agent Plugins

Quality-of-life plugins and reusable skills for AI agents, collected in one monorepo.

## Skills

- [`topic-to-html`](skills/topic-to-html/) — Turns a topic into a high-quality glass HTML explainer page.
- [`easy-to-trip`](skills/easy-to-trip/) — Turns a structured trip-data folder into a self-contained, mobile-first HTML trip page (or a static site folder). The skill name lives in `scripts/skill_meta.py` so it is easy to change.

## Layout

```text
skills/    # One folder per skill
plugins/   # Non-skill plugins, as they are added
```

## License

[MIT](LICENSE)
