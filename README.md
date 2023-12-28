# Shellbot

A Discord bot for monitoring and controlling jobs as a remote shell.

## Installation

In shell, run:
```sh
pip install git+https://github.com/patztablook22/genbot
```

Alternatively, specify the package in requirements.txt simply as:
```txt
git+https://github.com/patztablook22/shellbot
```

## Usage

Change your working directory to what you wish to be the working directory for the Shellbot application and run:
```sh
python3 -m shellbot path/to/config.json
```

The configuration file should contain the `token` for the discord bot and the allowed `users` and `roles`.
The `users` and `roles` specify the unique IDs of users/roles that one must have in order to interact with the Shellbot. Both can be specified either as
- `list` - the whitelist
- `dict` - keys `whitelist` and `blacklist`


An example configuration may look like the following:
```json
{
    "token": "xDFJDJkljsldfjSDFJoo28342",
    "users": [
        "12345678901234567890",
        "39201482034812093483"
    ]
}
```
