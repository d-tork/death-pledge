# death-pledge
From Middle French _mortgage_ and Old French _mort gage_ ("death pledge"), after a 
translation of judicial Medieval Latin _mortuum vadium_ or _mortuum wadium_. So
called because the deal dies either when the debt is paid or when payment fails.

## Installation
Based on [this article](https://godatadriven.com/blog/a-practical-guide-to-using-setup-py/)

Clone this repo, then create the environment
```
cd death-pledge
python3 -m venv venv && source venv/bin/activate
python -m pip install -r requirements.txt
```

Copy or create keys, tokens, config to the config/ dir.

Install the `deathpledge` module as editable
```
python -m pip install -e .[dev]
```

If you're using zsh and want to install extras for the dev environment, the bracket `[` has a 
special meaning and needs to be escaped:
```
python -m pip install -e '.[dev]'
```

**Note:** if you edit anything in `setup.py`, you will need to reinstall.

## Usage
Only with the proper credentials can this be run:
* Google OAuth for my spreadsheet, or else feed it your own list of URLs
* Real estate login
* Bing Maps API token

Run `python deathpledge --help` for a list of options

### Example usage
```
# [re]process the last 5 URLs added
python deathpledge -n 5

# process only new listings not already in database
python deathpledge --new
```

## Rebuilding and using the Docker image
```
docker build -t deathpledge:latest .
```

The entrypoint is the `deathpledge` module, so the `run` command accepts any command line arg that
the module would
```
# [re]process the last URL, even if it's Closed
docker run deathpledge -n 1 -f
```

### Entering the container interactively (for debugging)
```
docker run -it --entrypoint sh deathpledge
```
