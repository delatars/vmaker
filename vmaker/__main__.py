
def entry():
    """Entrypoint"""
    from vmaker.init.settings import LoadSettings
    LoadSettings()
    # from vmaker.core import Core
    # Core()


if __name__ == "__main__":
    entry()
