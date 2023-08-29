from flask_ngrok import run_with_ngrok
from flask import Flask, request

# 載入 LINE Message API 相關函式庫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
# 載入 json 標準函式庫，處理回傳的資料格式
import json
import requests
from bs4 import BeautifulSoup
# 讀取配置文件
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

access_token = config.get('access_token', '')
secret = config.get('secret', '')

app = Flask(__name__)

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True) # 取得收到的訊息內容
    try:
        json_data = json.loads(body) # json 格式化訊息內容
        line_bot_api = LineBotApi(access_token) # 確認token是否正確
        handler = WebhookHandler(secret) # 確認secret是否正確
        signature = request.headers['X-Line-Signature'] #加入回傳的headers
        handler.handle(body, signature) #綁定訊息回傳的相關資訊
        tk = json_data['events'][0]['replyToken'] #取得回傳訊息的Token
        type = json_data['events'][0]['message']['type'] #取得LINe收到的訊息類型
        if type=='text':
          msg = json_data['events'][0]['message']['text'] #取得 LINE收到的文字訊息
          print(msg) #印出內容
          if msg == '/菜單':
            url = get_menu()
            reply_image(url ,tk, access_token)
          elif msg == '/訂餐資訊':
            order_data = get_order() 
            reply_message(order_data, tk, access_token)
          elif "/我要訂餐" in msg: #訊息裡面只要有"我要訂餐"的字樣
            parts = msg.split() #使用空格拆分消息
            if len(parts) == 5: #確保消息內容都正確
              name = parts[1]
              phone = parts[2]
              order = parts[3]
              money = parts[4]
              order_data = [name, phone, order, money]
              confirm_msg = write_GoogleSheet(order_data) #返回是否成功寫入googlesheet的訊息
              reply_message(confirm_msg, tk, access_token) 
            else:
              reply_message("格式錯誤", tk, access_token)
          elif msg == "/指令":
            reply_msg = f"《指令教學》\n【/菜單】\n可查看今日菜單\n\n【/訂餐資訊】\n可查看今日訂餐的姓名、餐點及價錢\n\n【/我要訂餐 姓名 分機 餐點內容 價錢】\n!!記得要空白\n範例輸入(/我要訂餐 王曉明 1234 紅燒牛肉麵 120)\n可自動填入表單"
            reply_message(reply_msg, tk, access_token)
    except:
        print(body) # 如果發生錯誤，印出收到的內容
    return 'OK' # 驗證Webhook使用，不能省略

#獲取google表單的菜單圖片函式
def get_menu():
  #使用爬蟲去爬取google試算表的第一張圖片
  url = 'https://docs.google.com/forms/d/e/1FAIpQLSchJ10Xi_yPowfQxA2YMWrMlT0KyAgm0mhl0w7KGG2lK4r11A/viewform?fbzx=3986015554423091432'  
  response = requests.get(url)
  html_content = response.text
  # 使用Beautiful Soup解析HTML内容
  soup = BeautifulSoup(html_content, 'html.parser')
  # 查找第一個img標籤的內容
  img_tag = soup.find('img')
  if img_tag:
    image_url = img_tag.get('src')
    return image_url
  else:
    return ''

#獲取google試算表資訊的函式
def get_order():
  # App Script的URL
  url = 'https://script.google.com/macros/s/AKfycbx_axZf85Ne8bdk8zqwOkyYowQC35Wf58tgWSNrOF4fWoGj0y6rGMijgZPwTtDxRmvn_Q/exec'
  #response資料為json格式
  response = requests.get(url)
  data = response.json()
  formatted_data = []
  for index,item in enumerate(data, start=1): #起始index設為1
    formatted_item = f"{index}.姓名: {item['姓名']}\n 餐點名稱: {item['餐點名稱']}\n 金額: {item['金額']}" #將json格式更改為字串形式
    formatted_data.append(formatted_item)
  return '\n'.join(formatted_data)

#寫入googlesheet函式
def write_GoogleSheet(order_data):
  url = 'https://script.google.com/macros/s/AKfycbyteMRR981zuHDUchY-jeXb16Np-1dYQ4jGLCIlc-h58bGAX1OMCFg2xZ3RrNp8hb_TrQ/exec'
  json_data = json.dumps(order_data) #將資料轉換為json格式
  params = {
      'data': json_data
  }
  response = requests.get(url, params=params)
  if response.status_code == 200:
    try:
      if response.text:  # 检查响应内容是否为空
        data = response.json()
        if(data):
          return "訂餐完成"
        else:
          return "訂餐失敗"
      else:
        return "訂餐失敗，响应内容为空"
    except json.JSONDecodeError as e:
      print(f"JSON 解析错误: {e}")
  else:
    print(f"請求返回無效代碼: {response.status_code}")
  

# Line 回傳訊息函式
def reply_message(msg, rk, token):
    headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}
    body = {
    'replyToken':rk,
    'messages':[{
            "type": "text",
            "text": msg
        }]
    }
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/reply', headers=headers,data=json.dumps(body).encode('utf-8'))
    print(body)
    print(req.text)
# Line 回傳圖片函式
def reply_image(url, rk, token):
  headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}
  body = {
  'replyToken':rk,
  'messages':[{
        'type': 'image',
        'originalContentUrl': url,
        'previewImageUrl': url
      }]
  }
  req = requests.request('POST', 'https://api.line.me/v2/bot/message/reply', headers=headers,data=json.dumps(body).encode('utf-8'))
  print(body)
  print(req.text)

if __name__ == "__main__":
  run_with_ngrok(app)  #串連ngrok服務
  app.run()