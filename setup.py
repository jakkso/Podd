import setuptools

with open('README.md') as file:
    long_description = file.read()

setuptools.setup(
    name='Podd',
    version='0.1',
    author='Alexander Potts',
    author_email='alexander.potts@gmail.com',
    description='A Podcast downloader',
    long_description=long_description,
    url='https://github.com/jakkso/Podd',
    packages=setuptools.find_packages(),
    classifiers=(
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ),
)
