import importlib
import pkgutil

import app


def test_all_application_modules_import():
    for module in pkgutil.walk_packages(app.__path__, prefix="app."):
        importlib.import_module(module.name)
