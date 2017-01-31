from setuptools import find_packages, setup
from os import path
from codecs import open

HERE = path.abspath(path.dirname(__file__))
VERSION = (0, 1, 0)
__author__ = 'Vincent Lara'
__contact__ = "vincent.lara@data.gouv.fr"
__homepage__ = "https://github.com/"
__version__ = ".".join(map(str, VERSION))
__doc__ = "Models used by APITaxi"

def is_pkg(line):
    return line and not line.startswith(('--', 'git', '#'))

with open(path.join(HERE, 'requirements.txt'), encoding='utf-8') as reqs:
    install_requires = [l for l in reqs if is_pkg(l)]


setup(
    name='APITaxi_models',
    version=__version__,
    description=__doc__,
    url=__homepage__,
    author=__author__,
    author_email=__contact__,
    license='MIT',
    classifiers=[
        'Development Status :: 4 Beta',
        'Intended Audience :: Developpers',
        'Programming Language :: Python :: 2.7'
        ],
    keywords='taxi transportation',
    packages=find_packages(),
    install_requires=install_requires
)
