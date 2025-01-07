import email
import imaplib
import smtplib
import time
from email.header import decode_header
from email.message import EmailMessage
from queue import Queue
import re


class GmailProcessor:
    def __init__(self, mail: str, password: str, imap_server="imap.gmail.com"):
        self.EMAIL = mail
        self.PASSWORD = password
        self.IMAP_SERVER = imap_server
        self.email_queue = Queue()

    def read_email(self):
        """Đọc email từ inbox và thêm vào hàng đợi."""
        try:
            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER)
            mail.login(self.EMAIL, self.PASSWORD)
            mail.select("inbox")

            # Tìm các email chưa đọc
            status, messages = mail.search(None, "UNSEEN")
            email_ids = messages[0].split()

            for email_id in email_ids:
                # Lấy dữ liệu của email
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        from_ = msg.get("From")
                        date_ = msg.get("Date")

                        # Extract email address using regex
                        email_address = re.search(r"<(.+?)>", from_).group(1)

                        # Chỉ lấy các mail có subject chứa số, gạch ngang, còn lại bỏ qua
                        if re.match(r"^(vnsky|local)\d+", subject, re.IGNORECASE):
                            # Đưa email vào hàng đợi
                            self.email_queue.put(
                                {
                                    "subject": str(subject).strip(),
                                    "from": email_address,
                                    "date": date_,
                                }
                            )
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"Lỗi khi đọc email: {e}")

    def reply_email(self, original_email, reply_body):
        """Trả lời email đã nhận."""
        try:
            # Create the email message
            msg = EmailMessage()
            msg["Subject"] = f"Re: {original_email['subject']}"
            msg["From"] = self.EMAIL
            msg["To"] = original_email["from"]
            msg.set_content(reply_body)

            # Send the email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.EMAIL, self.PASSWORD)
                server.send_message(msg)
            print(f"Replied to email: {original_email['subject']}")
        except Exception as e:
            print(f"Lỗi khi trả lời email: {e}")

    def send_email(self, to_email, subject, body):
        """Gửi email."""
        try:
            # Create the email message
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.EMAIL
            msg["To"] = to_email
            msg.set_content(body)

            # Send the email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.EMAIL, self.PASSWORD)
                server.send_message(msg)
            print(f"Sent email to: {to_email}")
        except Exception as e:
            print(f"Lỗi khi gửi email: {e}")

    def process_email(self, handle_email):
        """Xử lý các email trong hàng đợi."""
        while True:
            try:
                if not self.email_queue.empty():
                    email_data = self.email_queue.get()
                    print("\n--- Processing Email ---")
                    print(f"Subject: {email_data['subject']}")
                    print(f"From: {email_data['from']}")
                    print(f"Date: {email_data['date']}")
                    print("------------------------")
                    # Callable: có thẻ pass 1 hàm xử lý email
                    handle_email(email_data)
                    # Hoàn thành tác vụ
                    self.email_queue.task_done()
                    # Delay 30s để tránh bị chặn
                    if (email_data['subject'].startswith('vnsky')):
                        time.sleep(30)
                else:
                    break
            except Exception as e:
                print(f"Lỗi khi xử lý email: {e}")

    def loop_forever(self, handle_email, time_sleep=15):
        print("Kiểm tra email...\n")
        while True:
            if self.email_queue.empty():
                self.read_email()
            if not self.email_queue.empty():
                print("Xử lý email và kích hoạt sim...")
                self.process_email(handle_email)
                print("\nKiểm tra email...")

            time.sleep(time_sleep)
