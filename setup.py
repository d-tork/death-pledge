from setuptools import setup, find_packages

setup(
    name='deathpledge',
    version='20.1',
    name='death-pledge',
    version='2020.11.22',
    author='Daniel Torkelson',
    packages=find_packages(include=['deathpledge', 'deathpledge.*']),
    entry_points={
        'console_scripts': [
            'main=deathpledge.main:main',
            'single=deathpledge.sample:main'
        ]
    },
    install_requires=[
        'beautifulsoup4',
        'cloudant',
        'Django',
        'fake-useragent',
        'google-api-python-client',
        'google-auth-httplib2',
        'google-auth-oauthlib',
        'numpy',
        'pandas',
        'PyYAML',
        'scipy',
        'selenium',
        'usaddress'
        ]
)
