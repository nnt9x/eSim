import os
import shutil

import pandas as pd
from dotenv import load_dotenv

from data.data import DataLoader
from local.bot import LocalBotAuto
from mailer.gmail import GmailProcessor
from vnsky.bot import VNSKYBot, CCCDException, SimCardException
import re

if __name__ == "__main__":
    # LOAD ENV
    load_dotenv()

    # EMAIL PROCESSOR
    email_processor = GmailProcessor(mail=os.getenv("EMAIL"), password=os.getenv("PASSWORD"))


    def split_string(input_str):
        match = re.match(r"([a-zA-Z]+)(\d+)", input_str)
        if match:
            letters = match.group(1)
            numbers = match.group(2)
            return letters, numbers
        else:
            return None, None


    # HANDLE EMAIL
    def handle_email(email_data):
        try:
            # TẢI DỮ LIỆU
            data_loader = DataLoader()
            df = data_loader.sim_data()

            # KIỂM TRA SỐ LƯỢNG SIM TRONG EXCEL
            not_activated = df[df["Trạng thái kích hoạt"].isna()]
            print(f"Số lượng sim chưa kích hoạt: {len(not_activated)}")

            if not_activated.size < 10:
                msg = "[Thông báo] Số lượng sim chưa kích hoạt còn lại " + str(not_activated);
                email_processor.send_email(os.getenv("ADMIN_MAIL"), msg.upper(), "")
            # KIỂM TRA SỐ LƯỢNG SIM TRONG EXCEL

            # KIỂM TRA SỐ LƯỢNG HỒ SƠ
            count_profiles = data_loader.get_count_profiles()
            print(f"Số lượng hồ sơ: {count_profiles}")

            if count_profiles == 0:
                email_processor.send_email(
                    os.getenv("ADMIN_MAIL"), "[THÔNG BÁO] HẾT ẢNH HỒ SƠ", ""
                )
                return

            elif count_profiles < 10:
                msg = "Số lượng hồ sơ còn lại " + str(count_profiles);
                email_processor.send_email(
                    os.getenv("ADMIN_MAIL"), msg.upper(), ""
                )
            # KIỂM TRA SỐ LƯỢNG HỒ SƠ

            subject = email_data["subject"]
            # Tách phần số và chữ từ subject
            mobile_network, serial = split_string(subject)
            mobile_network = str(mobile_network).upper()

            sim = df[(df["Nhà mạng"].str.upper().str.endswith(mobile_network)) & (df["Serial sim"].str.endswith(serial))]

            if sim.empty:
                email_processor.reply_email(
                    email_data, "Số serial và điện thoại không khớp!"
                )
                return

            # Lấy thông tin số điện thoại và serial chuẩn từ excel
            phone = sim.iloc[0]["Số điện thoại"]
            serial = sim.iloc[0]["Serial sim"]

            print(f"Kích hoạt sim - số điện thoại: {phone}, số serial: {serial}")

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

            elif (str(sim.iloc[0]['Nhà mạng']).upper() == "VNSKY"):
                print("KÍCH HOẠT CHO NHÀ MẠNG VNSKY")
                vnsky_bot = VNSKYBot(
                    os.getenv("SKY_EMAIL"),
                    os.getenv("SKY_PASSWORD")
                )
                try:
                    print("1. Đăng nhập")
                    vnsky_bot.login()
                    print("2. Check sim")
                    sim_card = vnsky_bot.check_sim(phone, serial)
                    print(sim_card.serial, sim_card.isdn)
                    print("3. Kiểm tra ảnh")
                    count = 10
                    profile = None
                    while (count > 0):
                        try:
                            profile = data_loader.get_first_profiles()
                            print(profile[0])
                            os.chmod(profile[0], 0o777)
                            cccd = vnsky_bot.check_card_cccd(profile[1], profile[2], profile[3])
                            break
                        except CCCDException as e:
                            count -= 1
                            print("Ảnh không hợp lệ, thử bộ hồ sơ khác", e)
                            os.chmod(profile[0], 0o777)
                            # Xoá hồ sơ không hợp lệ
                            try:
                                print("Xoá hồ sơ không hợp lệ")
                                shutil.move(profile[0], "data/profiles_failed")
                            except Exception as e:
                                print("Xoá hồ sơ không hợp lệ", e)
                    else:
                        # Email cho admin
                        # GỬI MAIL ADMIN NẾU CÓ LỖI
                        body_ = f""" Số điện thoại: {phone} và serial: {serial}, lỗi hồ sơ không hợp lệ"""
                        email_processor.send_email(
                            os.getenv("ADMIN_MAIL"), "XỬ LÝ LỖI KÍCH HOẠT SIM VNSKY", body_
                        )

                    print("4. Tạo mã khách hàng")
                    customer_no = vnsky_bot.gen_customer_no(cccd)
                    print(customer_no.customerCode)
                    print("5. Tạo mã hợp đồng")
                    contract_no = vnsky_bot.get_contactno(cccd)
                    print(contract_no.contractNo)
                    print("6. Tạo hợp đồng")
                    vnsky_bot.gen_contract(cccd, customer_no, contract_no, sim_card)
                    print("7. Kí hợp đồng")
                    vnsky_bot.create_signature(cccd=cccd, contract_no=contract_no)
                    print("8. Kích hoạt sim")
                    vnsky_bot.active_contract(
                        card_front=profile[1],
                        card_back=profile[2],
                        portrait=profile[3],
                        cccd=cccd,
                        customer_code=customer_no,
                        contact_no=contract_no,
                        sim_card=sim_card
                    );
                    email_processor.reply_email(email_data, "Kích hoạt sim thành công!")
                    try:
                        # Di chuyển hồ sơ đã kích hoạt
                        print("Di chuyển hồ sơ đã kích hoạt")
                        shutil.move(profile[0], "data/profiles_done")
                    except Exception as e:
                        print("Xoá hồ sơ không hợp lệ", e)
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

                except SimCardException as e:
                    email_processor.reply_email(email_data, "Sim đã kích hoạt hoặc số điện thoại, serial không đúng!")
                except Exception as e:
                    print(e)

        except Exception as e:
            print(f"Error: {e}")


    # LOOP FOREVER
    email_processor.loop_forever(handle_email)
