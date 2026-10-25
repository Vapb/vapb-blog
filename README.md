# vapb-blog

Personal blog where I write about AWS, cloud technologies, and software development.

🔗 **[vapb.github.io/vapb-blog](https://vapb.github.io/vapb-blog/)**

## Tech Stack

- [Hugo](https://gohugo.io/) — Static site generator
- [Vapb-Theme](https://github.com/Vapb/vapb-theme) — Theme
- GitHub Pages — Hosting

## Development

**Prerequisites:** Hugo installed ([installation guide](https://gohugo.io/installation/))

Start the local server:

```bash
hugo server --noHTTPCache
```

Post titles are limited to 60 characters (put the rest in `description`). Check before pushing; CI runs the same script:

```bash
python scripts/check_titles.py
```

Update theme (submodule):

```bash
git submodule update --recursive --remote
```