from PIL import Image
import pandas as pd
import os

class DataLoader:
    """
    Lấy dữ liệu esim và profiles
    """
    def sim_data(self, path="data/excel/sim.xlsx") -> pd.DataFrame:
        return pd.read_excel(path, dtype=str)

    def get_count_profiles(self, path="data/profiles"):
        """
        Lấy số lượng hồ sơ
        :return: số lượng hồ sơ
        """
        return len(os.listdir(path))

    def resize_and_compress_to_jpg(self, path, max_width=800, quality=80):
        try:
            img = Image.open(path)
            width, height = img.size
            # Nếu ảnh width bé hơn max_width thì không cần resize
            if width <= max_width:
                return
            if width > max_width:
                # Tính toán chiều cao mới dựa trên tỷ lệ khung hình
                new_height = int(height * (max_width / width))
                img = img.resize((max_width, new_height), Image.LANCZOS)  # Sử dụng LANCZOS để resize cho chất lượng tốt
            if img.mode != "RGB":
                img = img.convert("RGB")  # Chuyển đổi sang RGB để nén JPG hoạt động
            # Đổi đuôi ảnh sang jpg
            path = path.replace(".png", ".jpg").replace(".jpeg", ".jpg")
            img.save(path, "JPEG", optimize=True, quality=quality)  # Nén ảnh
        except FileNotFoundError:
            print(f"Lỗi: Không tìm thấy tệp ảnh tại: {path}")
        except Exception as e:
            print(f"Lỗi trong quá trình xử lý ảnh: {e}")

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
        # Tìm các file ảnh có đuôi .png hoặc .jpg hoặc .jpeg
        data = [file for file in data if file.endswith((".png", ".jpg", ".jpeg"))]
        # Nếu không có file ảnh thì thông báo lỗi
        if len(data) == 0:
            raise Exception("Không có file ảnh!")
        # Nếu có file ảnh thì nén và resize ảnh
        for file in data:
            self.resize_and_compress_to_jpg(os.path.abspath(f"{dir_path}/{file}"))
        # Trả về đường dẫn tuyệt đối của thư mục và các file ảnh
        data = [os.path.abspath(f"{dir_path}/{file}") for file in data]
        data.insert(0, dir_path)
        return data
