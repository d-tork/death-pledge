from setuptools import setup, find_packages

setup(
    name='deathpledge',
    version='20.1',
    author='Daniel Torkelson',
    packages=find_packages(include=['deathpledge', 'deathpledge.*']),
    install_requires=[
        'beautifulsoup4',
        'cloudant',
        'fake-useragent',
        'google-api-core',
        'google-api-python-client',
        'google-auth',
        'google-auth-httplib2',
        'google-auth-oauthlib',
        'googleapis-common-protos',
        'gspread',
        'httplib2',
        'numpy',
        'pandas',
        'probableparsing',
        'PyYAML',
        'rsa',
        'selenium',
        'sqlparse',
        'urllib3',
        'usaddress'
    ],
    entry_points={
        'console_scripts': [
            'main=deathpledge.main:main',
            'single=deathpledge.sample:main'
        ]
    }
)
