from setuptools import setup, find_packages

setup(
    name='death-pledge',
    version='2021.03.26',
    author='Daniel Torkelson',
    packages=find_packages(include=['deathpledge', 'deathpledge.*']),
    install_requires=[
        'beautifulsoup4',
        'cloudant',
        'Django',
        'fake-useragent',
        'google-api-python-client',
        'oauthlib',
        'google-auth',
        'numpy',
        'pandas',
        'PyYAML',
        'scipy',
        'selenium',
        'tqdm',
        'usaddress',
        ],
    extras_require={
        'dev': ['pytest', 'wheel']
    }
)
