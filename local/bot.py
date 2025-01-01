import requests
import json
import time

class LocalBase:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "content-type": "application/json",
        "dnt": "1",
        "origin": "https://kichhoat.sodepmoi.com",
        "priority": "u=1, i",
        "referer": "https://kichhoat.sodepmoi.com/",
        "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    }

    def __init__(self, username: str, password: str, appcode="TELCO_NPP"):
        self.username = username
        self.password = password
        self.appcode = appcode

class LocalBotAuto(LocalBase):
    # Thuộc tính
    distributor_id = 15870
    distributor_name = ""
    serial_number = None
    phone_number = None
    sim_type = None
    mbf_code = None
    order_id = None

    def __login(
        self, url="https://api-digital.asimgroup.vn/auth-twoid-service/v2/login"
    ):
        payload = json.dumps(
            {
                "username": self.username,
                "password": self.password,
                "appCode": self.appcode,
            }
        )
        response = requests.request("POST", url, headers=self.headers, data=payload)

        # Kiểm tra response có status = 200
        if response.status_code != 200:
            raise Exception("Đăng nhập thất bại!")

        # Lấy access token
        accessToken = response.json()["response"]["accessToken"]
        tokenType = response.json()["response"]["tokenType"]

        self.headers["authorization"] = f"{tokenType} {accessToken}"

        return True

    def __get_sim_info(
        self,
        serial_number: str,
        url="https://api.localshop.vn/lcs-new/api/Provider/check-picked-serial-sim",
    ):
        payload = json.dumps(
            {
                "distributorId": 15870,  # Fixed
                "serialNumber": serial_number,
            }
        )
        response = requests.request("POST", url, headers=self.headers, data=payload)
        # Kiểm tra response có status = 200
        if response.status_code != 200:
            raise Exception("Sim đã kích hoạt hoặc số serial không đúng!")

        if response.json()["isSucceeded"] == True:
            data = response.json()
            self.serial_number = data["data"]["serialNumber"]
            self.phone_number = data["data"]["phoneNumber"]
            self.sim_type = data["data"]["simType"]
            self.mbf_code = data["data"]["mbfCode"]
            self.distributor_id = data["data"]["distributorId"]
            self.distributor_name = data["data"]["distributorName"]

    def __activate_sim(
        self,
        url="https://api.localshop.vn/lcs-new/api/Provider/active-sim-by-enterprise-single",
    ):
        payload = json.dumps(
            {
                "createdBy": self.distributor_name,
                "phoneNumber": self.phone_number,
                "serialNumber": self.serial_number,
                "pool": 0,
                "distributorId": self.distributor_id,
                "mbfCode": self.mbf_code,
                "simType": self.sim_type,
            }
        )
        response = requests.request("POST", url, headers=self.headers, data=payload)

        # Kiểm tra response có status = 200
        if response.status_code != 200:
            raise Exception("Kích hoạt sim thất bại!")
        else:
            data = response.json()
            self.order_id = data["data"]["orderId"]
            pass

    def getOrder(self, serial, order_id):
        url = f"https://api.localshop.vn/lcs-new/api/Provider/get-detail-history-active?Serial={serial}&OrderId={order_id}"
        response = requests.request("GET", url, headers=self.headers)

        if response.status_code != 200:
            raise Exception("Lấy thông tin đơn hàng thất bại!")
        else:
            data = response.json()
            return data["data"]

    def auto_activate(self, serial_number):
        self.__login()
        self.__get_sim_info(serial_number)
        print(
            self.phone_number, self.serial_number, self.mbf_code, self.distributor_name
        )
        self.__activate_sim()
        time.sleep(3)
        order = self.getOrder(serial_number, self.order_id)
        return (order["phoneNumber"], order["serial"], order["linkQrText"])

