import requests

def check_email_exists(email):
    api_key = '84a02d1ec4c44c7491ecaa97eb821d81'  # 🛑 Thay API Key tại đây
    url = f"https://emailvalidation.abstractapi.com/v1/?api_key={api_key}&email={email}"

    try:
        response = requests.get(url)
        result = response.json()

        print("📨 Checking email:", email)
        print("📋 Response:", result)

        if result.get('deliverability') == 'DELIVERABLE':
            return True
        else:
            return False
    except Exception as e:
        print("❌ API Error:", e)
        return False


# 🧪 Test thử:
if __name__ == "__main__":
    test_email = input("Nhập email để kiểm tra: ")
    if check_email_exists(test_email):
        print("✅ Email tồn tại và có thể gửi OTP.")
    else:
        print("❌ Email không tồn tại hoặc không gửi được.")
