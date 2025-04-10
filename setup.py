from setuptools import setup, find_packages


with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setup(
    name="stockcli",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "stockcli=app.main:cli",
        ],
    },
    python_requires=">=3.7",
    author="Admas Terefe Girma",
    author_email="aadmasterefe00@gmail.com",
    description="A command-line tool for fetching stock exchange data from TwelveData API",
    keywords="cli, stocks, trading, finance, twelvedata",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)