from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="basic_calculator",
    version="1.0",
    packages=find_packages(),
    install_requires=["pytest==6.2.5", "dataclasses==0.7.1"],
    description="A basic calculator implementation in Python",
    long_description=long_description,
    long_description_content_type="text/markdown"
)