import pandas as pd
import sqlite3
import os


class DataLoader:
    def sim_data(self, path="data/excel/sim.xlsx") -> pd.DataFrame:
        return pd.read_excel(path, dtype=str)

    def get_count_profiles(self, path="data/profiles"):
        """
        Lấy số lượng hồ sơ
        :return: số lượng hồ sơ
        """
        return len(os.listdir(path))

    def get_first_profiles(self, path="data/profiles"):
        """
        Lấy ra ảnh và thư mục
        :param path: đường dẫn đến thư mục chứa ảnh
        :return: thư mục được chọn và các file ảnh
        """
        first_dir = os.listdir(path)[0]
        dir_path = os.path.abspath(f"{path}/{first_dir}")
        data = os.listdir(dir_path)
        if len(data) == 0:
            raise Exception("Không có file ảnh!")
        # Trả về đường dẫn tuyệt đối của thư mục và các file ảnh
        data = [os.path.abspath(f"{dir_path}/{file}") for file in data]
        data.insert(0, dir_path)
        return data
