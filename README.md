# lazyfeed

![Loaded screenshot](./.github/screenshot-loaded.png)

`lazyfeed` is a dead simple terminal base RSS/Atom reader built using [Textual](https://www.textualize.io/).

## WIP

`lazyfeed` is under active development. Right now you can add feeds, load the pending articles, and mark them as read. However, I plan to keep adding features, including:

- Configuration options.
- Docker support.
- Filtering.
- The ability to mark articles as favorites.
- More Vim-like keybindings for a better navigation.
- Saving articles for later.
- Themes.
- Viewing articles directly within the terminal, without needing to open a browser.

> Please note that `lazyfeed` is a personal project, and the features I will be developing are tailored to my own needs and preferences.

## Motivation

I wanted a simple and fast way to follow RSS feeds directly in my terminal, without relying on services like [Feedly](https://feedly.com/) or similar platforms. While there are existing solutions such as [newsboat](https://github.com/newsboat/newsboat) and [nom](https://github.com/guyfedwards/nom), I wanted to create my own solution. And here it is.

## Install

There are several ways to install `lazyfeed`:

### Via `pip`

```bash
pip install lazyfeed
```

### Via [`pipx`](https://github.com/pypa/pipx) (recommended)

```bash
pipx install lazyfeed
```

## Usage

```bash
lazyfeed add https://dnlzrgz.com/rss # Add a feed.
lazyfeed add https://dnlzrgz.com/rss https://www.theverge.com/rss/index.xml # Add multiple feeds at once.
lazyfeed import feeds.opml # Import from an OPML file.
lazyfeed # Start the TUI
```

> In addition to importing, you can also export all your feeds using the export command. Run `lazyfeed export --help` for more information.

## Store

`lazyfeed` uses a SQLite database to store all your feeds and posts.This database is located at `$XDG_CONFIG_HOME/lazyfeed/lazyfeed.db`.

## Dependencies

- [click](https://click.palletsprojects.com/en/8.1.x/).
- [Textual](https://www.textualize.io/).
- [aiohttp](https://docs.aiohttp.org/en/stable/index.html).
- [feedparser](https://feedparser.readthedocs.io/en/latest/basic.html).
- [sqlalchemy](https://www.sqlalchemy.org/).

## Screenshots

![Mark all as read screenshot](./.github/screenshot-mark-all-as-read.png)
![Help screenshot](./.github/screenshot-help.png)
