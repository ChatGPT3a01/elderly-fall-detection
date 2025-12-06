"""
LINE Bot 測試腳本 - 測試訊息發送功能
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 添加模組路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_bot.bot import LineBotNotifier


def test_line_bot():
    """測試 LINE Bot 功能"""
    print("=" * 50)
    print("LINE Bot 測試程式")
    print("=" * 50)
    print()

    # 從環境變數讀取設定
    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
    secret = os.getenv('LINE_CHANNEL_SECRET', '')
    user_id = os.getenv('LINE_USER_ID', '')

    print(f"Channel Access Token: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
    print(f"User ID: {user_id}")
    print()

    if not token or token == 'your_channel_access_token_here':
        print("錯誤：請先在 .env 檔案中設定 LINE_CHANNEL_ACCESS_TOKEN")
        return False

    if not user_id or user_id == 'your_user_id_here':
        print("錯誤：請先在 .env 檔案中設定 LINE_USER_ID")
        return False

    # 建立通知器
    notifier = LineBotNotifier(token, secret, user_id)

    # 測試 1：發送純文字訊息
    print("測試 1：發送純文字訊息...")
    success1 = notifier.send_text_message("測試訊息：樂齡防傾倒系統運作正常！")
    print()

    # 測試 2：發送 Flex Message
    print("測試 2：發送 Flex Message...")
    success2 = notifier.send_flex_message(
        severity="mild",
        angle=38.5,
        timestamp=datetime.now()
    )
    print()

    # 測試結果
    print("=" * 50)
    print("測試結果：")
    print(f"  純文字訊息：{'成功' if success1 else '失敗'}")
    print(f"  Flex Message：{'成功' if success2 else '失敗'}")
    print("=" * 50)

    if success1 or success2:
        print("\n請檢查您的 LINE 是否收到訊息！")
    else:
        print("\n發送失敗，請檢查以下項目：")
        print("1. LINE_CHANNEL_ACCESS_TOKEN 是否正確")
        print("2. LINE_USER_ID 是否正確")
        print("3. LINE Bot 是否已經加入您的好友")

    return success1 and success2


if __name__ == '__main__':
    test_line_bot()
