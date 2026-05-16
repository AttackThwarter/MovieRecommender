import requests

print("در حال تلاش برای اتصال به LM Studio...")
try:
    response = requests.get("http://localhost:8087/v1/models", proxies={"http": None, "https": None})
    if response.status_code == 200:
        print("✅ اتصال کاملاً موفق بود! سرور زنده است.")
        print("مدل‌های در دسترس:", response.json())
    else:
        print(f"⚠️ سرور پیدا شد اما ارور داد. کد ارور: {response.status_code}")
except Exception as e:
    print("❌ اتصال شکست خورد. جزئیات ارور:")
    print(e)