from setuptools import setup, find_packages
import sotawhat

setup(
    name='sotawhat',
    version=str(sotawhat.__VERSION__),
    packages=find_packages(),
    description='arxiv scanner based on sotawhat',
    long_description=str('arxiv scanner is a script to query Arxiv for the latest '
                         'abstracts and extract summaries from them. '),
    license="",
    install_requires=['six', 'pyspellchecker'],
    entry_points={
        'console_scripts': ['scan=sotawhat.scan:main'],
    }
)
