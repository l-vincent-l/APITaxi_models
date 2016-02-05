from setuptools import find_packages, setup
import APITaxi_models
from os import path
from codecs import open

HERE = path.abspath(path.dirname(__file__))

def is_pkg(line):
    return line and not line.startswith(('--', 'git', '#'))

with open(path.join(HERE, 'requirements.txt'), encoding='utf-8') as reqs:
    install_requires = [l for l in reqs if is_pkg(l)]


setup(
    name='APITaxi_models',
    version=APITaxi_models.__version__,
    description=APITaxi_models.__doc__,
    url=APITaxi_models.__homepage__,
    author=APITaxi_models.__author__,
    author_email=APITaxi_models.__contact__,
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
