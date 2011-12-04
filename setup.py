import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "django-chained",
    version = "0.2",
    author = "Tim Mann",
    author_email = "tdmann@whaba.mn",
    description = ("A cascading selection app for Django."),
    license = "MIT",
    keywords = "cascading select chain django form chained",
    url = "https://github.com/tdmann/django-chained",
    packages=['chained'],
    long_description=read('README.markdown'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
    ],
)