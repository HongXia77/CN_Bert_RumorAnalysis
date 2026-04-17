import sys
import pkg_resources

print("Python Version:")
print(sys.version)
print("\nInstalled Packages:")
for pkg in pkg_resources.working_set:
    print(f"{pkg.key}=={pkg.version}")