# lazyfeed

![Loaded screenshot](./.github/screenshot-loaded.png)

`lazyfeed` is a dead simple terminal base RSS/Atom reader built using [Textual](https://www.textualize.io/).

## Features

- Save posts for later.
- Vim-like keybindings for a better navigation.

> For a better experience using a [nerd font](https://www.nerdfonts.com/) is recommended.

## WIP

`lazyfeed` is under active development. Right now you can add feeds, load the pending posts, and mark them as read. However, I plan to keep adding features, including:

- Configuration options.
- Docker support.
- Filtering.
- The ability to mark posts as favorites.
- Themes.
- Viewing posts directly within the terminal, without needing to open a browser.

> Please note that `lazyfeed` is a personal project, and the features I will be developing are tailored to my own needs and preferences.

## Motivation

I wanted a simple and fast way to follow RSS feeds directly in my terminal, without relying on services like [Feedly](https://feedly.com/) or similar platforms. While existing tools like [newsboat](https://github.com/newsboat/newsboat) and [nom](https://github.com/guyfedwards/nom) are available and there are more mature, I wanted to create my own, and here it is.

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

## Keybindings

### General

- `?`: Display/Close help message.
- `q/esc`: Quit.
- `r`: Refresh.

### Navigation

- `j/n`: Move to next post.
- `k/p`: Move to previous post.
- `gg/G`: Jump to first/last post.
- `ga`: Pending posts.
- `gl`: Saved posts.

### Posts

- `o/enter`: Open link in browser and mark post as read.
- `x`: Mark post as read.
- `m`: Mark post as read without removing it.
- `shift+a`: Mark all posts as read.

## Store

`lazyfeed` uses a SQLite database to store all your feeds and posts. This database is located at `$XDG_CONFIG_HOME/lazyfeed/lazyfeed.db`.

## Dependencies

- [click](https://click.palletsprojects.com/en/8.1.x/).
- [Textual](https://www.textualize.io/).
- [aiohttp](https://docs.aiohttp.org/en/stable/index.html).
- [feedparser](https://feedparser.readthedocs.io/en/latest/basic.html).
- [sqlalchemy](https://www.sqlalchemy.org/).

## Screenshots

![Mark all as read screenshot](./.github/screenshot-mark-all-as-read.png)
![Saved for later screenshot](./.github/screenshot-saved.png)
![Help screenshot](./.github/screenshot-help.png)
