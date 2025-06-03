import os
import importlib

# Dynamically import all modules in the current package
__all__ = []

package_dir = os.path.dirname(__file__)
for module_name in os.listdir(package_dir):
    if module_name.endswith(".py") and module_name != "__init__.py":
        module = module_name[:-3]  # Strip the .py extension
        imported_module = importlib.import_module(f".{module}", package=__name__)
        __all__.append(module)