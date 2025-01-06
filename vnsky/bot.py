import requests
from streamlit import header
from datetime import datetime
import json
from signature.signature import create_text_image

class CCCDException(Exception):
    def __init__(self, message):
        super().__init__(message)

class SimCardException(Exception):
    def __init__(self, message):
        super().__init__(message)

class SimCard:
    def __init__(self, isdn=None, serial=None, imsi=None, registerDate=None, pckCode=None, pckName=None, apiCode=None,
                 apiPromCode=None, smsCode=None, smsPromCode=None, profileType=None, activationCode=None, simType=None):
        self.isdn = str(isdn)
        self.serial = str(serial)
        self.imsi = imsi
        self.registerDate = registerDate
        self.pckCode = pckCode
        self.pckName = pckName
        self.apiCode = apiCode
        self.apiPromCode = apiPromCode
        self.smsCode = smsCode
        self.smsPromCode = smsPromCode
        self.profileType = profileType
        self.activationCode = activationCode
        self.simType = simType


class ContractNo:
    def __init__(self, contractNo):
        self.contractNo = str(contractNo)


class CustomerCode:
    def __init__(self, customerCode):
        self.customerCode = str(customerCode)


class CCCD:
    def __init__(self, c06SuccessMessage, nationality, document, name, id, issue_by, issue_date, birthday, sex, address,
                 city, district, ward, expiry, id_ekyc, check_sendOTP, list_phoneNumber, total_sim, errors, c06_errors):
        self.c06SuccessMessage = c06SuccessMessage
        self.nationality = str(nationality)
        self.document = str(document)
        self.name = str(name)
        self.id = str(id)
        self.issue_by = str(issue_by)
        self.issue_date = str(issue_date).replace("-", "/")
        self.birthday = str(birthday).replace("-", "/")
        self.sex = str(sex)
        self.address = str(address)
        self.city = str(city)
        self.district = str(district)
        self.ward = str(ward)
        self.expiry = str(expiry).replace("-", "/")
        self.id_ekyc = str(id_ekyc)
        self.check_sendOTP = check_sendOTP
        self.list_phoneNumber = list_phoneNumber
        self.total_sim = total_sim
        self.errors = errors
        self.c06_errors = c06_errors


class VNSKYBot:

    def __init__(self, username:str, password:str):
        self.__username = username
        self.__password = password
        self.__token = None
        self.__headers = {
            'accept': '*',
            'accept-language': 'vi-VN',
            'authorization': 'Basic dm5za3ktaW50ZXJuYWw6RkwySjFZNDJxVndSUHZK',  # Tìm sau
            'content-type': 'application/x-www-form-urlencoded',
            'dnt': '1',
            'origin': 'https://bcss-uat.vnsky.vn',
            'priority': 'u=1, i',
            'referer': 'https://bcss-uat.vnsky.vn/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
        }

    def login(self, url="https://api-bcss-uat.vnsky.vn/admin-service/private/oauth2/token"):
        payload = f'grant_type=password&client_identity=VNSKY&username={self.__username}&password={self.__password}'
        response = requests.request("POST", url, headers=self.__headers, data=payload)
        if response.status_code == 200:
            access_token = response.json().get('access_token')
            token_type = response.json().get('token_type')
            self.__token = f"{token_type} {access_token}"
            # Cập nhật lại headers
            self.__headers['authorization'] = self.__token
        else:
            raise Exception(f"Đăng nhập thất bại! {response.text}")

    def check_sim(self, phone_number: str, serial: str) -> SimCard:
        url = f"https://api-bcss-uat.vnsky.vn/customer-service/private/api/v1/check-sim-active-status?serial={serial}&isdn={phone_number}"
        response = requests.request("GET", url, headers=self.__headers)
        if response.status_code != 200:
            raise SimCardException(f"Số thuê bao đã được kích hoạt")
        simcard = SimCard(**response.json())
        simcard.isdn = phone_number
        return simcard

    def check_card_cccd(self, card_front, card_back, portrait,
                        url="https://api-bcss-uat.vnsky.vn/customer-service/private/api/v1/activation-info?cardType=1") -> CCCD:
        payload = {'enableActiveMore3': '0'}
        files = []
        try:
            with open(card_front, 'rb') as f1, open(card_back, 'rb') as f2, open(portrait, 'rb') as f3:
                files = [
                    ('cardFront', ('1.jpg', f1, 'image/jpeg')),
                    ('cardBack', ('2.jpg', f2, 'image/jpeg')),
                    ('portrait', ('3.jpg', f3, 'image/jpeg'))
                ]
                # Xóa content-type
                self.__headers.pop('content-type', None)

                response = requests.request("POST", url, headers=self.__headers, data=payload, files=files)
                if response.status_code != 200:
                    raise CCCDException(f"Xác thực thông tin CCCD thất bại")
                else:
                    if response.json().get('check_sendOTP') == True:
                        raise CCCDException(f"Xác thực thông tin CCCD thất bại, cần nhập OTP")
                # Lấy căn cước công dân
                return CCCD(**response.json())
        except Exception as e:
            raise CCCDException(f"Error handling files: {e}")

    def get_contactno(self, cccd: CCCD) -> ContractNo:
        url = f"https://api-bcss-uat.vnsky.vn/customer-service/private/api/v1/gen-contract-no?idNo={cccd.id}&activeType=1"
        self.__headers['content-type'] = 'application/x-www-form-urlencoded'
        response = requests.request("POST", url, headers=self.__headers)

        if response.status_code != 200:
            raise Exception(f"Lấy thông tin hợp đồng thất bại")
        return ContractNo(**response.json())

    def gen_customer_no(self, cccd: CCCD):
        url = f"https://api-bcss-uat.vnsky.vn/customer-service/private/api/v1/gen-customer-code?idNo={cccd.id}"
        self.__headers['content-type'] = 'application/x-www-form-urlencoded'
        response = requests.request("POST", url, headers=self.__headers)
        if response.status_code != 200:
            raise Exception(f"Tạo mã khách hàng thất bại")
        return CustomerCode(**response.json())

    def gen_contract(self, cccd: CCCD, customer_code: CustomerCode, contact_no: ContractNo, sim_card: SimCard,
                     url="https://api-bcss-uat.vnsky.vn/customer-service/private/api/v1/gen-contract"):
        payload = json.dumps({
            "codeDecree13": [
                "DK1",
                "DK2",
                "DK3",
                "DK4",
                "DK5",
                "DK6"
            ],
            "contractNo": contact_no.contractNo,
            "customerId": customer_code.customerCode,
            "ccdvvt": "HCM001",
            "contractDate": datetime.now().strftime("%d/%m/%Y"),
            "customerName": cccd.name,
            "gender": cccd.sex,
            "birthDate": cccd.birthday,
            "idNo": cccd.id,
            "idDate": cccd.issue_date,
            "idPlace": cccd.issue_by,
            "address": cccd.address,
            "type": "PNG",
            "phoneNumber": sim_card.isdn,
            "phoneLists": [
                {
                    "phoneNumber": sim_card.isdn,
                    "serialSim": sim_card.serial,
                    "packagePlan": sim_card.pckCode
                }
            ],
        }, ensure_ascii=False)
        self.__headers['content-type'] = 'application/json'
        response = requests.request("POST", url, headers=self.__headers, data=payload)
        if response.status_code != 200:
            raise Exception(f"Tạo hợp đồng thất bại")


    def create_signature(self, cccd: CCCD, contract_no: ContractNo,
                         url="https://api-bcss-uat.vnsky.vn/customer-service/public/api/v1/gen-contract/submit"):
        payload = {'contractNo': contract_no.contractNo}
        # Tạo chữ kí theo tên
        image_signature = create_text_image(cccd.name)

        with open(image_signature, 'rb') as image_file:
            image_data = image_file.read()
        files = [
            ('signature', ('blob', image_data, 'application/octet-stream'))
        ]
        self.__headers.pop('content-type', None)
        response = requests.request("POST", url, headers=self.__headers, data=payload, files=files)

        if response.status_code != 200:
            raise Exception(f"Ký hợp đồng thất bại")

    def active_contract(self, card_front, card_back, portrait, cccd: CCCD, customer_code: CustomerCode,
                        contact_no: ContractNo, sim_card: SimCard,
                        url="https://api-bcss-uat.vnsky.vn/customer-service/private/api/v1/activate"):
        payload = {
            'data': json.dumps({
                "request": {
                    "strSex": cccd.sex,
                    "strSubName": cccd.name,
                    "strIdNo": cccd.id,
                    "strIdIssueDate": cccd.issue_date,
                    "strIdIssuePlace": cccd.issue_by,
                    "strBirthday": cccd.birthday,
                    "strProvince": cccd.city,
                    "strDistrict": cccd.district,
                    "strPrecinct": cccd.ward,
                    "strHome": cccd.address,
                    "strAddress": cccd.address,
                    "strContractNo": contact_no.contractNo,
                    "strIsdn": sim_card.isdn,
                    "strSerial": sim_card.serial,
                },
                "idExpiryDate": cccd.expiry,
                "idType": cccd.document,
                "idEkyc": cccd.id_ekyc,
                "customerCode": customer_code.customerCode,
                "constractDate": datetime.now().strftime("%d/%m/%Y"),
            }, ensure_ascii=False)
        }

        files = [
            ('front', ('1.jpg', open(card_front, 'rb'), 'image/jpeg')),
            ('back', ('2.jpg', open(card_back, 'rb'), 'image/jpeg')),
            ('portrait', ('3.jpg', open(portrait, 'rb'), 'image/jpeg'))
        ]

        self.__headers.pop('content-type', None)
        response = requests.request("POST", url, headers=self.__headers, data=payload, files=files)
        if response.status_code != 200:
            raise Exception("Kích hoạt sim thất bại!", response.json())
        return response.json()

    def activate_subscription(self, phone: str, serial: str, front_image: str, back_image: str, portrait: str) -> bool:
        print("1. Đăng nhập")
        self.login()
        print("2. Check sim")
        sim_card = self.check_sim(phone, serial)
        print(sim_card.serial, sim_card.isdn)
        print("3. Kiểm tra ảnh")
        cccd = self.check_card_cccd(front_image, back_image, portrait)
        print("CCCD", cccd.name, cccd.id, cccd.expiry)
        return
        print("4. Tạo mã khách hàng")
        customer_no = self.gen_customer_no(cccd)
        print(customer_no.customerCode)
        print("5. Tạo mã hợp đồng")
        contract_no = self.get_contactno(cccd)
        print(contract_no.contractNo)
        print("6. Tạo hợp đồng")
        self.gen_contract(cccd, customer_no, contract_no, sim_card)
        print("7. Kí hợp đồng")
        self.create_signature(cccd=cccd, contract_no=contract_no)
        print("8. Kích hoạt sim")
        self.active_contract(
            card_front=front_image,
            card_back=back_image,
            portrait=portrait,
            cccd=cccd,
            customer_code=customer_no,
            contact_no=contract_no,
            sim_card=sim_card
        );
