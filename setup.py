from setuptools import setup, find_packages

setup(
    name="OraTAPI",
    version="1.0.6",
    description="Oracle TAPI Application",
    author="Your Name",
    author_email="your_email@example.com",
    packages=find_packages(),  
    include_package_data=True,  # Include files from the MANIFEST.in
    package_data={  # Include non-Python files in specific packages
        "templates": ["**/*.tpt", "**/*.tpt.sample"],
    },
    data_files=[  # Include root-level files and other extras
        (".", ["setup.py", "LICENSE", "setup.sh", "requirements.txt", "README.md"]),
    ],
    entry_points={
        "console_scripts": [
            "conn_mgr=controller.conn_mgr:main",
            "ora_tapi=controller.ora_tapi:main",
        ]
    },
)
