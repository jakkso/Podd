import setuptools

with open('README.md') as file:
    long_description = file.read()

requirements = [
    'feedparser',
    'jinja2',
    'mutagen'

]

setuptools.setup(
    name='Podd',
    version='0.1.3',
    author='Alexander Potts',
    author_email='alexander.potts@gmail.com',
    description='A Podcast downloader',
    long_description=long_description,
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
)

