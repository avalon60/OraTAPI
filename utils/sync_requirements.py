""" Use this with caution - experimental! """
import re

# Define paths for requirements.txt and pyproject.toml
requirements_file = "requirements.txt"
toml_file = "pyproject.toml"

# Read the dependencies from requirements.txt
with open(requirements_file, "r") as f:
    dependencies = f.readlines()

# Clean up the dependencies list (remove comments, empty lines, etc.)
dependencies = [line.strip() for line in dependencies if line.strip() and not line.startswith("#")]

# Read the existing pyproject.toml file
with open(toml_file, "r") as f:
    toml_content = f.readlines()

# Find the `[project.dependencies]` section or create it if it doesn't exist
dependencies_section_start = None
for idx, line in enumerate(toml_content):
    if line.strip() == "[project.dependencies]":
        dependencies_section_start = idx
        break

if dependencies_section_start is None:
    # If the section doesn't exist, create it
    toml_content.append("\n[project.dependencies]\n")
    dependencies_section_start = len(toml_content) - 1

# Add dependencies to the pyproject.toml file
for dep in dependencies:
    # Make sure the line contains '==', meaning it's a valid dependency with version
    if '==' in dep:
        dep_name, dep_version = dep.split("==", 1)  # Split on the first occurrence of '=='
        toml_content.insert(dependencies_section_start + 1, f"{dep_name} = \"{dep_version}\"\n")
    else:
        print(f"Skipping invalid dependency: {dep}")

# Write the updated content back to pyproject.toml
with open(toml_file, "w") as f:
    f.writelines(toml_content)

print("Dependencies updated in pyproject.toml!")
