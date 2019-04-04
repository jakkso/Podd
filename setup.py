import setuptools

from podd.settings import Config

with open('README.md') as file:
    long_description = file.read()

requirements = [
    'feedparser',
    'jinja2',
    'mutagen',
    'click',
    'keyring'
]

setuptools.setup(
    name='Podd',
    version=Config.version,
    author='Alexander Potts',
    author_email='alexander.potts@gmail.com',
    description='A Podcast downloader',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/jakkso/Podd',
    packages=setuptools.find_packages(),
    classifiers=(
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'podd = podd.__main__:podd'
        ]
    },
    include_package_data=True,
    data_files=[('podd/templates', ['podd/templates/base.txt',
                                    'podd/templates/base.html',
                                    'podd/templates/_podcast.html'])]
)
