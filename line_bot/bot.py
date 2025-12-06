"""
LINE Bot 通知模組 - Python 版本
提供 LINE Bot Push Message 功能
"""

import os
import sys
import json
import base64
from datetime import datetime
from typing import Optional
import requests
import threading

# 修正 Windows 控制台編碼問題
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


class LineBotNotifier:
    """
    LINE Bot 通知發送器
    使用 LINE Messaging API 發送推播訊息
    """

    # LINE Messaging API 端點
    PUSH_MESSAGE_URL = "https://api.line.me/v2/bot/message/push"
    BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"

    def __init__(self,
                 channel_access_token: str,
                 channel_secret: str,
                 user_id: Optional[str] = None):
        """
        初始化 LINE Bot 通知器

        Args:
            channel_access_token: LINE Bot Channel Access Token
            channel_secret: LINE Bot Channel Secret
            user_id: 目標用戶 ID（用於 Push Message）
        """
        self.channel_access_token = channel_access_token
        self.channel_secret = channel_secret
        self.user_id = user_id

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }

    def send_text_message(self,
                          text: str,
                          user_id: Optional[str] = None) -> bool:
        """
        發送文字訊息

        Args:
            text: 訊息內容
            user_id: 目標用戶 ID（若未提供則使用初始化時的 user_id）

        Returns:
            是否發送成功
        """
        target_user = user_id or self.user_id
        if not target_user:
            print("錯誤：未提供目標用戶 ID")
            return False

        payload = {
            "to": target_user,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }

        try:
            response = requests.post(
                self.PUSH_MESSAGE_URL,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ 訊息發送成功")
                return True
            else:
                print(f"❌ 訊息發送失敗: {response.status_code}")
                print(f"錯誤訊息: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print(f"❌ 發送訊息逾時")
            return False
        except Exception as e:
            print(f"❌ 發送訊息時發生錯誤: {e}")
            return False

    def send_fall_alert(self,
                        severity: str,
                        angle: Optional[float] = None,
                        timestamp: Optional[datetime] = None,
                        screenshot_path: Optional[str] = None,
                        user_id: Optional[str] = None) -> bool:
        """
        發送跌倒警示訊息

        Args:
            severity: 危險程度（"mild" 或 "severe"）
            angle: 軀幹傾斜角度
            timestamp: 事件時間戳
            screenshot_path: 截圖檔案路徑
            user_id: 目標用戶 ID

        Returns:
            是否發送成功
        """
        target_user = user_id or self.user_id
        if not target_user:
            print("錯誤：未提供目標用戶 ID")
            return False

        # 設定時間戳
        event_time = timestamp or datetime.now()
        time_str = event_time.strftime("%Y-%m-%d %H:%M:%S")

        # 根據嚴重程度設定訊息
        if severity == "severe":
            severity_text = "🚨 嚴重"
            emoji = "🆘"
        else:
            severity_text = "⚠️ 輕微"
            emoji = "⚡"

        # 組建訊息
        messages = []

        # 主要警示訊息
        alert_text = f"""{emoji} 跌倒偵測警報 {emoji}

偵測到可能跌倒，請立即查看！

⏰ 時間：{time_str}
📊 危險程度：{severity_text}"""

        if angle is not None:
            alert_text += f"\n📐 軀幹傾斜角度：{angle:.1f}°"

        alert_text += "\n\n請盡快確認長者安全狀況！"

        messages.append({
            "type": "text",
            "text": alert_text
        })

        # 如果有截圖，發送圖片
        if screenshot_path and os.path.exists(screenshot_path):
            # 注意：LINE Messaging API 需要圖片為 HTTPS URL
            # 本地圖片需要先上傳到伺服器才能發送
            # 這裡提供一個替代方案：將圖片編碼為 base64 並提示用戶
            pass

        payload = {
            "to": target_user,
            "messages": messages
        }

        try:
            response = requests.post(
                self.PUSH_MESSAGE_URL,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ 跌倒警示發送成功")
                return True
            else:
                print(f"❌ 跌倒警示發送失敗: {response.status_code}")
                print(f"錯誤訊息: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print(f"❌ 發送警示逾時")
            return False
        except Exception as e:
            print(f"❌ 發送警示時發生錯誤: {e}")
            return False

    def send_flex_message(self,
                          severity: str,
                          angle: Optional[float] = None,
                          timestamp: Optional[datetime] = None,
                          user_id: Optional[str] = None) -> bool:
        """
        發送 Flex Message 格式的跌倒警示（更美觀的卡片樣式）

        Args:
            severity: 危險程度
            angle: 軀幹傾斜角度
            timestamp: 事件時間戳
            user_id: 目標用戶 ID

        Returns:
            是否發送成功
        """
        target_user = user_id or self.user_id
        if not target_user:
            print("錯誤：未提供目標用戶 ID")
            return False

        event_time = timestamp or datetime.now()
        time_str = event_time.strftime("%Y-%m-%d %H:%M:%S")

        # 根據嚴重程度設定顏色
        if severity == "severe":
            header_color = "#DC3545"
            severity_text = "嚴重警告"
        else:
            header_color = "#FFC107"
            severity_text = "輕微警告"

        # Flex Message 內容
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🚨 跌倒偵測警報",
                        "color": "#FFFFFF",
                        "weight": "bold",
                        "size": "lg"
                    }
                ],
                "backgroundColor": header_color,
                "paddingAll": "15px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "偵測到可能跌倒！",
                        "weight": "bold",
                        "size": "xl",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": "請立即查看長者狀況",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "md"
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "時間",
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": time_str,
                                        "size": "sm",
                                        "color": "#333333",
                                        "flex": 2
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "嚴重程度",
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": severity_text,
                                        "size": "sm",
                                        "color": header_color,
                                        "weight": "bold",
                                        "flex": 2
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "請盡快確認安全狀況！",
                        "color": "#DC3545",
                        "size": "sm",
                        "align": "center",
                        "weight": "bold"
                    }
                ],
                "paddingAll": "10px"
            }
        }

        # 如果有角度資訊，添加到內容中
        if angle is not None:
            angle_box = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "傾斜角度",
                        "color": "#666666",
                        "size": "sm",
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": f"{angle:.1f}°",
                        "size": "sm",
                        "color": "#333333",
                        "flex": 2
                    }
                ]
            }
            flex_content["body"]["contents"][3]["contents"].append(angle_box)

        payload = {
            "to": target_user,
            "messages": [
                {
                    "type": "flex",
                    "altText": "跌倒偵測警報 - 偵測到可能跌倒！",
                    "contents": flex_content
                }
            ]
        }

        try:
            response = requests.post(
                self.PUSH_MESSAGE_URL,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ Flex Message 發送成功")
                return True
            else:
                print(f"❌ Flex Message 發送失敗: {response.status_code}")
                print(f"錯誤訊息: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print(f"❌ 發送 Flex Message 逾時")
            return False
        except Exception as e:
            print(f"❌ 發送 Flex Message 時發生錯誤: {e}")
            return False

    def broadcast_message(self, text: str) -> bool:
        """
        廣播訊息給所有用戶

        Args:
            text: 訊息內容

        Returns:
            是否發送成功
        """
        payload = {
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }

        try:
            response = requests.post(
                self.BROADCAST_URL,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ 廣播訊息發送成功")
                return True
            else:
                print(f"❌ 廣播訊息發送失敗: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            print(f"❌ 廣播訊息逾時")
            return False
        except Exception as e:
            print(f"❌ 廣播訊息時發生錯誤: {e}")
            return False

    def _upload_image_to_imgbb(self, image_path: str, api_key: str = None) -> Optional[str]:
        """
        上傳圖片到 imgbb.com 並取得 URL

        Args:
            image_path: 本地圖片路徑
            api_key: imgbb API 金鑰（可從環境變數 IMGBB_API_KEY 讀取）

        Returns:
            圖片的 HTTPS URL，失敗則返回 None
        """
        # 從環境變數讀取 API 金鑰
        if api_key is None:
            api_key = os.getenv('IMGBB_API_KEY', '')

        if not api_key:
            print("⚠️ 未設定 IMGBB_API_KEY，無法上傳圖片")
            return None

        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            response = requests.post(
                'https://api.imgbb.com/1/upload',
                data={
                    'key': api_key,
                    'image': image_data,
                    'expiration': 600  # 圖片 10 分鐘後過期
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']['url']

            print(f"❌ 上傳圖片失敗: {response.text}")
            return None

        except Exception as e:
            print(f"❌ 上傳圖片時發生錯誤: {e}")
            return None

    def send_image_message(self,
                           image_path: str,
                           user_id: Optional[str] = None) -> bool:
        """
        發送圖片訊息

        Args:
            image_path: 本地圖片路徑
            user_id: 目標用戶 ID

        Returns:
            是否發送成功
        """
        target_user = user_id or self.user_id
        if not target_user:
            print("錯誤：未提供目標用戶 ID")
            return False

        if not os.path.exists(image_path):
            print(f"錯誤：圖片檔案不存在: {image_path}")
            return False

        # 上傳圖片取得 URL
        image_url = self._upload_image_to_imgbb(image_path)

        if not image_url:
            # 如果上傳失敗，發送提示訊息
            return self.send_text_message(
                f"📸 已截圖儲存於本機：{os.path.basename(image_path)}\n（若需查看截圖，請設定 IMGBB_API_KEY 環境變數）",
                target_user
            )

        payload = {
            "to": target_user,
            "messages": [
                {
                    "type": "image",
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url
                }
            ]
        }

        try:
            response = requests.post(
                self.PUSH_MESSAGE_URL,
                headers=self.headers,
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                print(f"✅ 圖片訊息發送成功")
                return True
            else:
                print(f"❌ 圖片訊息發送失敗: {response.status_code}")
                print(f"錯誤訊息: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print(f"❌ 發送圖片訊息逾時")
            return False
        except Exception as e:
            print(f"❌ 發送圖片訊息時發生錯誤: {e}")
            return False

    @staticmethod
    def load_config(config_path: str) -> dict:
        """
        從設定檔載入 LINE Bot 設定

        Args:
            config_path: 設定檔路徑

        Returns:
            設定字典
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('line_bot', {})


def create_notifier_from_config(config_path: str) -> LineBotNotifier:
    """
    從設定檔建立 LINE Bot 通知器

    Args:
        config_path: 設定檔路徑

    Returns:
        LineBotNotifier 實例
    """
    config = LineBotNotifier.load_config(config_path)

    return LineBotNotifier(
        channel_access_token=config.get('channel_access_token', ''),
        channel_secret=config.get('channel_secret', ''),
        user_id=config.get('user_id')
    )


# 使用範例
if __name__ == '__main__':
    # 範例：從設定檔建立通知器
    import os

    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    if os.path.exists(config_path):
        notifier = create_notifier_from_config(config_path)

        # 發送測試訊息
        notifier.send_text_message("測試訊息：系統正常運作中！")

        # 發送跌倒警示
        notifier.send_fall_alert(
            severity="mild",
            angle=38.5,
            timestamp=datetime.now()
        )

        # 發送 Flex Message
        notifier.send_flex_message(
            severity="severe",
            angle=55.0
        )
    else:
        print(f"設定檔不存在：{config_path}")
        print("請先設定 config.json 中的 LINE Bot 資訊")
