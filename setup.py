from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in frappe_whatsapp_waha/__init__.py
from frappe_whatsapp_waha import __version__ as version

setup(
    name="frappe_whatsapp_waha",
    version=version,
    description="WhatsApp integration for Frappe using the WAHA API (forked from shridarpatil/frappe_whatsapp)",
    author="djs4000",
    author_email="djs4000@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
