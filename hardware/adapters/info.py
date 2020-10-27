from pathlib import Path


class PackInfo:
    def get_available_adapters(self) -> list:
        path = Path(__file__).resolve().parent
        dir_list = [item.parts[-1] for item in path.iterdir() if str(item.parts[-1])[0] != '_' and item.is_dir()]
        dir_list.sort()
        return dir_list