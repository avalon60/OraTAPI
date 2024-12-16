from setuptools import setup, find_packages

setup(
    name="OraTAPI",
    version="1.0.3",
    
    # Automatically find all packages by searching the current directory
    packages=find_packages(),  # Automatically finds all packages
    
    # Include shell scripts and other non-Python files
    package_data={
        '': ['bin/ora_tapi.sh', 'bin/conn_mgr.sh'],  # Package data
    },
    
    entry_points={
        "console_scripts": [
            "ora_tapi=controller.ora_tapi:main",  # Adjust the entry point to the actual function
            "conn_mgr=controller.conn_mgr:main",  # Likewise for conn_mgr
        ],
    },
    include_package_data=True,  # Ensure package data is included
)

