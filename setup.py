import pathlib
from setuptools import setup, find_packages

README = (pathlib.Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="selldatatoai",
    version="1.0.1",
    description="Python client for the AI Data Value Score API from selldatatoai.com: score company domains 0 to 100 for the data AI buyers want, one at a time or in batches of 100.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Alpha Quantum",
    author_email="info@alpha-quantum.com",
    url="https://www.selldatatoai.com",
    project_urls={
        "Homepage": "https://www.selldatatoai.com",
        "Documentation": "https://www.selldatatoai.com/api/",
        "Source": "https://github.com/explainableaixai/selldatatoai-python",
        "Pricing": "https://www.selldatatoai.com/pricing/",
        "Demo": "https://www.selldatatoai.com/data-asset-score/",
    },
    license="MIT",
    packages=find_packages(exclude=("tests", "test")),
    install_requires=["requests>=2.20"],
    python_requires=">=3.7",
    entry_points={"console_scripts": ["selldatatoai=selldatatoai.__main__:_entry"]},
    keywords=["sell data to ai", "ai data value score", "ai training data", "ai data broker", "company data api",
              "lead scoring", "firmographics", "technographics", "data licensing", "b2b data", "domain intelligence"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Office/Business",
    ],
)
