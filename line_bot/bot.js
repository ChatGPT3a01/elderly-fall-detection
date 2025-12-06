/**
 * LINE Bot 通知模組 - Node.js 版本
 * 提供 LINE Bot Push Message 功能
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

class LineBotNotifier {
    /**
     * LINE Bot 通知發送器
     */

    static PUSH_MESSAGE_URL = '/v2/bot/message/push';
    static BROADCAST_URL = '/v2/bot/message/broadcast';

    /**
     * 初始化 LINE Bot 通知器
     * @param {string} channelAccessToken - LINE Bot Channel Access Token
     * @param {string} channelSecret - LINE Bot Channel Secret
     * @param {string} userId - 目標用戶 ID
     */
    constructor(channelAccessToken, channelSecret, userId = null) {
        this.channelAccessToken = channelAccessToken;
        this.channelSecret = channelSecret;
        this.userId = userId;
    }

    /**
     * 發送 HTTP POST 請求
     * @param {string} endpoint - API 端點
     * @param {object} payload - 請求內容
     * @returns {Promise<boolean>}
     */
    _sendRequest(endpoint, payload) {
        return new Promise((resolve, reject) => {
            const data = JSON.stringify(payload);

            const options = {
                hostname: 'api.line.me',
                port: 443,
                path: endpoint,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.channelAccessToken}`,
                    'Content-Length': Buffer.byteLength(data)
                }
            };

            const req = https.request(options, (res) => {
                let responseData = '';

                res.on('data', (chunk) => {
                    responseData += chunk;
                });

                res.on('end', () => {
                    if (res.statusCode === 200) {
                        console.log('✅ 訊息發送成功');
                        resolve(true);
                    } else {
                        console.log(`❌ 訊息發送失敗: ${res.statusCode}`);
                        console.log(`錯誤訊息: ${responseData}`);
                        resolve(false);
                    }
                });
            });

            req.on('error', (e) => {
                console.log(`❌ 發送訊息時發生錯誤: ${e.message}`);
                reject(e);
            });

            req.write(data);
            req.end();
        });
    }

    /**
     * 發送文字訊息
     * @param {string} text - 訊息內容
     * @param {string} userId - 目標用戶 ID
     * @returns {Promise<boolean>}
     */
    async sendTextMessage(text, userId = null) {
        const targetUser = userId || this.userId;
        if (!targetUser) {
            console.log('錯誤：未提供目標用戶 ID');
            return false;
        }

        const payload = {
            to: targetUser,
            messages: [
                {
                    type: 'text',
                    text: text
                }
            ]
        };

        return await this._sendRequest(LineBotNotifier.PUSH_MESSAGE_URL, payload);
    }

    /**
     * 發送跌倒警示訊息
     * @param {string} severity - 危險程度 ("mild" 或 "severe")
     * @param {number} angle - 軀幹傾斜角度
     * @param {Date} timestamp - 事件時間戳
     * @param {string} userId - 目標用戶 ID
     * @returns {Promise<boolean>}
     */
    async sendFallAlert(severity, angle = null, timestamp = null, userId = null) {
        const targetUser = userId || this.userId;
        if (!targetUser) {
            console.log('錯誤：未提供目標用戶 ID');
            return false;
        }

        const eventTime = timestamp || new Date();
        const timeStr = eventTime.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });

        let severityText, emoji;
        if (severity === 'severe') {
            severityText = '🚨 嚴重';
            emoji = '🆘';
        } else {
            severityText = '⚠️ 輕微';
            emoji = '⚡';
        }

        let alertText = `${emoji} 跌倒偵測警報 ${emoji}\n\n`;
        alertText += `偵測到可能跌倒，請立即查看！\n\n`;
        alertText += `⏰ 時間：${timeStr}\n`;
        alertText += `📊 危險程度：${severityText}`;

        if (angle !== null) {
            alertText += `\n📐 軀幹傾斜角度：${angle.toFixed(1)}°`;
        }

        alertText += '\n\n請盡快確認長者安全狀況！';

        const payload = {
            to: targetUser,
            messages: [
                {
                    type: 'text',
                    text: alertText
                }
            ]
        };

        return await this._sendRequest(LineBotNotifier.PUSH_MESSAGE_URL, payload);
    }

    /**
     * 發送 Flex Message 格式的跌倒警示
     * @param {string} severity - 危險程度
     * @param {number} angle - 軀幹傾斜角度
     * @param {Date} timestamp - 事件時間戳
     * @param {string} userId - 目標用戶 ID
     * @returns {Promise<boolean>}
     */
    async sendFlexMessage(severity, angle = null, timestamp = null, userId = null) {
        const targetUser = userId || this.userId;
        if (!targetUser) {
            console.log('錯誤：未提供目標用戶 ID');
            return false;
        }

        const eventTime = timestamp || new Date();
        const timeStr = eventTime.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });

        let headerColor, severityText;
        if (severity === 'severe') {
            headerColor = '#DC3545';
            severityText = '嚴重警告';
        } else {
            headerColor = '#FFC107';
            severityText = '輕微警告';
        }

        const infoContents = [
            {
                type: 'box',
                layout: 'horizontal',
                contents: [
                    {
                        type: 'text',
                        text: '時間',
                        color: '#666666',
                        size: 'sm',
                        flex: 1
                    },
                    {
                        type: 'text',
                        text: timeStr,
                        size: 'sm',
                        color: '#333333',
                        flex: 2
                    }
                ]
            },
            {
                type: 'box',
                layout: 'horizontal',
                contents: [
                    {
                        type: 'text',
                        text: '嚴重程度',
                        color: '#666666',
                        size: 'sm',
                        flex: 1
                    },
                    {
                        type: 'text',
                        text: severityText,
                        size: 'sm',
                        color: headerColor,
                        weight: 'bold',
                        flex: 2
                    }
                ]
            }
        ];

        if (angle !== null) {
            infoContents.push({
                type: 'box',
                layout: 'horizontal',
                contents: [
                    {
                        type: 'text',
                        text: '傾斜角度',
                        color: '#666666',
                        size: 'sm',
                        flex: 1
                    },
                    {
                        type: 'text',
                        text: `${angle.toFixed(1)}°`,
                        size: 'sm',
                        color: '#333333',
                        flex: 2
                    }
                ]
            });
        }

        const flexContent = {
            type: 'bubble',
            header: {
                type: 'box',
                layout: 'vertical',
                contents: [
                    {
                        type: 'text',
                        text: '🚨 跌倒偵測警報',
                        color: '#FFFFFF',
                        weight: 'bold',
                        size: 'lg'
                    }
                ],
                backgroundColor: headerColor,
                paddingAll: '15px'
            },
            body: {
                type: 'box',
                layout: 'vertical',
                contents: [
                    {
                        type: 'text',
                        text: '偵測到可能跌倒！',
                        weight: 'bold',
                        size: 'xl',
                        margin: 'md'
                    },
                    {
                        type: 'text',
                        text: '請立即查看長者狀況',
                        size: 'sm',
                        color: '#666666',
                        margin: 'md'
                    },
                    {
                        type: 'separator',
                        margin: 'lg'
                    },
                    {
                        type: 'box',
                        layout: 'vertical',
                        margin: 'lg',
                        spacing: 'sm',
                        contents: infoContents
                    }
                ]
            },
            footer: {
                type: 'box',
                layout: 'vertical',
                contents: [
                    {
                        type: 'text',
                        text: '請盡快確認安全狀況！',
                        color: '#DC3545',
                        size: 'sm',
                        align: 'center',
                        weight: 'bold'
                    }
                ],
                paddingAll: '10px'
            }
        };

        const payload = {
            to: targetUser,
            messages: [
                {
                    type: 'flex',
                    altText: '跌倒偵測警報 - 偵測到可能跌倒！',
                    contents: flexContent
                }
            ]
        };

        return await this._sendRequest(LineBotNotifier.PUSH_MESSAGE_URL, payload);
    }

    /**
     * 廣播訊息給所有用戶
     * @param {string} text - 訊息內容
     * @returns {Promise<boolean>}
     */
    async broadcastMessage(text) {
        const payload = {
            messages: [
                {
                    type: 'text',
                    text: text
                }
            ]
        };

        return await this._sendRequest(LineBotNotifier.BROADCAST_URL, payload);
    }

    /**
     * 從設定檔載入 LINE Bot 設定
     * @param {string} configPath - 設定檔路徑
     * @returns {object}
     */
    static loadConfig(configPath) {
        const configData = fs.readFileSync(configPath, 'utf8');
        const config = JSON.parse(configData);
        return config.line_bot || {};
    }
}

/**
 * 從設定檔建立 LINE Bot 通知器
 * @param {string} configPath - 設定檔路徑
 * @returns {LineBotNotifier}
 */
function createNotifierFromConfig(configPath) {
    const config = LineBotNotifier.loadConfig(configPath);

    return new LineBotNotifier(
        config.channel_access_token || '',
        config.channel_secret || '',
        config.user_id || null
    );
}

// 使用範例
async function main() {
    const configPath = path.join(__dirname, '..', 'config.json');

    if (fs.existsSync(configPath)) {
        const notifier = createNotifierFromConfig(configPath);

        // 發送測試訊息
        await notifier.sendTextMessage('測試訊息：系統正常運作中！');

        // 發送跌倒警示
        await notifier.sendFallAlert('mild', 38.5, new Date());

        // 發送 Flex Message
        await notifier.sendFlexMessage('severe', 55.0);
    } else {
        console.log(`設定檔不存在：${configPath}`);
        console.log('請先設定 config.json 中的 LINE Bot 資訊');
    }
}

// 匯出模組
module.exports = {
    LineBotNotifier,
    createNotifierFromConfig
};

// 如果直接執行此檔案
if (require.main === module) {
    main().catch(console.error);
}
