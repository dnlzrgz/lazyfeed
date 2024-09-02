# lazyfeed

![Loaded screenshot](./.github/screenshot-loaded.png)

`lazyfeed` is a dead simple terminal base RSS/Atom reader built using [Textual](https://www.textualize.io/).

## Features

- Save posts for later.
- Mark posts as favorite.
- Vim-like keybindings.
- Custom configuration.
- Filtering (Coming soon).
- Theming (Coming soon).
- In-App view (Coming soon).
- Docker support (Coming soon).

> `lazyfeed` is a personal project, and the features I will be working on are tailored to my own needs and preferences at the moment.

## Motivation

I wanted a simple and fast way to follow RSS feeds directly in my terminal, without relying on services like [Feedly](https://feedly.com/) or similar platforms. While existing tools like [newsboat](https://github.com/newsboat/newsboat) and [nom](https://github.com/guyfedwards/nom) are available and there are more mature, I wanted to create my own, and here it is.

## Install

There are several ways to install `lazyfeed`:

### Via `pip`

```bash
pip install lazyfeed
```

### Via [`pipx`](https://github.com/pypa/pipx)

```bash
pipx install lazyfeed

```

### Via [`uv`](https://github.com/astral-sh/uv)

```bash
uv tool add lazyfeed

# Or

uvx lazyfeed
```

## Usage

> For a better experience using a [nerd font](https://www.nerdfonts.com/) is recommended.

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
- `gp/gn`: Pending/New posts.
- `ga`: All posts.
- `gl`: Saved posts.
- `gf`: Posts marked as favorite.

### Posts

- `o/enter`: Open link in browser and mark post as read.
- `x`: Mark post as read.
- `m`: Mark post as read without removing it.
- `s`: Save post for later.
- `f`: Mark post as favorite.
- `shift+a`: Mark all posts as read.

## Store

`lazyfeed` uses a SQLite database to store all your feeds and posts. This database is located at `$XDG_CONFIG_HOME/lazyfeed/lazyfeed.db`.

## Configuration

If you need to, you can customize some aspects of `lazyfeed`. Below is an example of a `config.toml` file that allows you to configure the `aiohttp` client used by `lazyfeed`.

```config.toml
[client]
connect_timeout=10
timeout=300

[client.headers]
User-Agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
Accept = "gzip, deflate, br"
Accept-Language = "en-US,en;q=0.6"
Accept-Encoding = "gzip, deflate, br"
```

> The `config.toml` file should be placed in the $XDG_CONFIG_HOME/lazyfeed/ directory.

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
