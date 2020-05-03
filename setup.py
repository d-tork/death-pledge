from setuptools import setup, find_packages

setup(
    name='deathpledge',
    version='20.1',
    packages=find_packages(include=['deathpledge', 'deathpledge.*']),
    entry_points={
        'console_scripts': [
            'main=deathpledge.main:main',
            'single=deathpledge.sample:main'
        ]
    }
)
