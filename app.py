import os
import shutil

import pandas as pd
from dotenv import load_dotenv

from data.data import DataLoader
from local.bot import LocalBotAuto
from mailer.gmail import GmailProcessor
from vnsky.bot import VNSKYBot

if __name__ == "__main__":
    # LOAD ENV
    load_dotenv()

    # EMAIL PROCESSOR
    email_processor = GmailProcessor(mail=os.getenv("EMAIL"), password=os.getenv("PASSWORD"))

    # INIT LOCALBOT AUTO
    local_bot = LocalBotAuto(
        os.getenv("LOCAL_USER"),
        os.getenv("LOCAL_PASSWORD")
    )
    # INIT VNSKYBOT AUTO
    vnsky_bot = VNSKYBot(
        os.getenv("SKY_EMAIL"),
        os.getenv("SKY_PASSWORD")
    )

    # HANDLE EMAIL
    def handle_email(email_data, phone:str, serial:str):
        try:
            # Tải dữ liệu mới nhất từ excel
            data_loader = DataLoader()
            df = data_loader.sim_data()

            # In thời gian hiện tại
            print(f"Kích hoạt sim - số điện thoại: {phone}, số serial: {serial}")

            # KIỂM TRA SỐ LƯỢNG THÔNG TIN SIM
            not_activated = df[df["Trạng thái kích hoạt"].isna()]
            print(f"Số lượng sim chưa kích hoạt: {len(not_activated)}")

            if not_activated.size < 10:
                msg = "[Thông báo] Số lượng sim chưa kích hoạt còn lại " + str(not_activated);
                email_processor.send_email(os.getenv("ADMIN_MAIL"), msg.upper(),"")

            # KIỂM TRA SỐ LƯỢNG HỒ SƠ
            count_profiles = data_loader.get_count_profiles()
            print(f"Số lượng hồ sơ: {count_profiles}")

            if count_profiles == 0:
                email_processor.send_email(
                    os.getenv("ADMIN_MAIL"), "[THÔNG BÁO] HẾT ẢNH HỒ SƠ", ""
                )
                return

            elif count_profiles < 10:
                msg =  "Số lượng hồ sơ còn lại " + str(count_profiles);
                email_processor.send_email(
                    os.getenv("ADMIN_MAIL"), msg.upper(),""
                )

            # LẤY THÔNG TIN SỐ ĐIỆN THOẠI
            sim = df[(df["Số điện thoại"] == phone) & (df["Serial sim"] == serial)]

            # Nếu không tìm thấy sim
            if sim.empty:
                email_processor.reply_email(
                    email_data, "Số serial và điện thoại không khớp!"
                )
                return

            # Nếu sim đã kích hoạt
            if sim["Trạng thái kích hoạt"].values[0] == "Đã kích hoạt":
                email_processor.reply_email(email_data, "Sim đã được kích hoạt, vui lòng kiểm tra lại thông tin!")
                return

            # THỰC HIỆN KÍCH HOẠT SIM THEO NHÀ MẠNG
            if (str(sim.iloc[0]['Nhà mạng']).upper() == "LOCAL"):
                print("KÍCH HOẠT CHO NHÀ MẠNG LOCAL")
                local_bot = LocalBotAuto(
                    os.getenv("LOCAL_USER"),
                    os.getenv("LOCAL_PASSWORD")
                )
                try:
                    result = local_bot.auto_activate(serial)
                    # Reply email
                    body_ = f"""
                        KÍCH HOẠT THÀNH CÔNG
                        Số điện thoại: 0{result[0]}
                        Số Serial: {result[1]}
                        {'Mã QR: ' + result[2] if result[2] is not None else ''}
                    """

                    email_processor.reply_email(email_data, body_)
                    # LƯU THÔNG TIN HỒ SƠ VÀO EXCEL
                    df.loc[sim.index, "Trạng thái kích hoạt"] = "Đã kích hoạt"
                    df.loc[sim.index, "Mail gửi kích hoạt"] = email_data["from"]
                    df.loc[sim.index, "Thời gian gửi"] = email_data["date"]
                    df.loc[sim.index, "Thời gian kích hoạt"] = (
                        pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
                    )
                    # Cập nhật SĐT với LOCAL
                    df.loc[sim.index, "Số điện thoại"] = result[0]
                    df.to_excel("data/excel/sim.xlsx", index=False)

                except Exception as e:
                    # GỬI MAIL ADMIN NẾU CÓ LỖI
                    body_ = f"""
                            Số điện thoại: {phone} và serial: {serial}
                        """
                    email_processor.send_email(
                        os.getenv("ADMIN_MAIL"), "XỬ LÝ LỖI KÍCH HOẠT SIM LOCAL", body_
                    )

            else:
                print("KÍCH HOẠT CHO NHÀ MẠNG VNSKY")
                # KICH HOAT VOI VNSKY
                profile = data_loader.get_first_profiles()
                os.chmod(profile[0], 0o777)
                # Kích hoạt sim
                counter = 2
                # Gửi hồ sơ
                result = False
                while counter > 0:
                    result = vnsky_bot.activate_subscription(
                        phone, serial, profile[1], profile[2], profile[3]
                    )
                    if result:
                        email_processor.reply_email(email_data, "Kích hoạt sim thành công!")
                        shutil.move(profile[0], "../data/profiles_done")
                        # Lưu thông tin hồ sơ
                        df.loc[sim.index, "Trạng thái kích hoạt"] = "Đã kích hoạt"
                        df.loc[sim.index, "Mail gửi kích hoạt"] = email_data["from"]
                        df.loc[sim.index, "Thời gian gửi"] = email_data["date"]
                        # Thời gian hiện tại d/m/y h:m:s
                        df.loc[sim.index, "Thời gian kích hoạt"] = (
                            pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
                        )
                        # Lưu dữ liệu
                        df.to_excel("data/excel/sim.xlsx", index=False)
                        break
                    counter = counter - 1

                    if counter == 1:
                        # Hai lần kích hoạt trước lỗi -> đổi hình
                        shutil.move(profile[0], "../data/profiles_failed")
                        profile = data_loader.get_first_profiles()
                        os.chmod(profile[0], 0o777)
                else:
                    body_ = f"""
                    Số điện thoại: {phone} và serial: {serial}"""
                    email_processor.send_email(
                        os.getenv("ADMIN_MAIL"), "XỬ LÝ LỖI KÍCH HOẠT SIM VNSKY", body_
                    )
                    shutil.move(profile[0], "../data/profiles_failed")

        except Exception as e:
            print(f"Error: {e}")

    # LOOP FOREVER
    email_processor.loop_forever(handle_email)
