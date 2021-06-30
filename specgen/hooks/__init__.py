import glob
import importlib
import warnings

from os.path import dirname, basename, isfile, join

modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules
           if isfile(f)
           and not f.endswith('__init__.py')
           and not f.startswith("_")]


class HookWarning(UserWarning):
    pass


for module in __all__:
    try:
        importlib.import_module("." + module, package = __name__)
    except ImportError as e:
        warnings.warn(f"Unable to import hook {module}. This hook will not be available.\n{e}",
                      HookWarning, 2)
