from setuptools import setup, find_packages

setup(
    name="pictocode",
    version="0.1.0",
    description="Un mini-éditeur graphique façon Canvas en PyQt5",
    author="Vous",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15"
    ],
    entry_points={
        "gui_scripts": [
            "pictocode = pictocode.__main__:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: PyQt5"
    ],
)
