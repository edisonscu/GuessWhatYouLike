from urllib.parse import parse_qs
import os
import json
import configparser
import logging
import requests
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
from linebot.models import LocationSendMessage
from linebot.exceptions import LineBotApiError
import apiai
from templates.RestuarantBubble import RestuarantBubble
from templates.ActivityBubble import ActivityBubble
from templates.ScenicSpotBubble import ScenicSpotBubble
from templates.LodgingBubble import LodgingBubble
from utils.db import getRestuarantsByPref
import pymongo
import boto3

# Channel Access Token
line_bot_api = LineBotApi(os.environ.get('ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.environ.get('CHANNEL_SECERT'))


def lambda_handler(lambda_event, context):
    # get X-Line-Signature header value
    signature = lambda_event['headers']['X-Line-Signature']
    # get request body as text
    body = lambda_event['body']

    @handler.add(PostbackEvent)
    def handle_postback(event):
        data = parse_qs(event.postback.data)
        #print("data:"+data)
        line_bot_api.reply_message(
            event.reply_token, LocationSendMessage(
                title=data['title'][0],
                address=data['address'][0],
                latitude=data['lat'][0],
                longitude=data['lng'][0]
            )
        )

    # 處理訊息
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        # 連ALTAS
        userId = event.source.user_id
        client = pymongo.MongoClient("mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/test?retryWrites=true&w=majority") 
        db = client.data
        collection = db.user
        condition = {'userId': userId}
        user = collection.find_one(condition)

        text = event.message.text
        language = 'zh-TW'
        country = translate_text(text,"auto","en")# 防止系統以為簡體轉繁體產生error，先轉成en
        if (country.get('SourceLanguageCode') == "zh"):  
            zh_text = country.get('TranslatedText')
            text = translate_text(zh_text,"en","zh-TW").get('TranslatedText')
        else:
            result = translate_text(text,"auto","zh-TW")  # 轉成中文
            language = result.get('SourceLanguageCode') #偵測使用者語言
            text = result.get('TranslatedText')
            print('SourceLanguageCode: ' + language)
        print('TranslatedText: ' + text)
        
        if text == "餐廳":
            print(event.message.text)
            # user沒資料
            if user == None or user['lat'] == None:
                language = "zh-TW"
                if user:
                    language = user['lan']

                relocation = {
                    'zh-TW' : 'https://i.imgur.com/Mu3OmsY.jpg',
                    'en' : 'https://imgur.com/QPeSsju.jpg',
                    'ja' : 'https://imgur.com/MjuLXTe.jpg',
                    'ko' : 'https://imgur.com/2uu74Xs.jpg'
                }.get(user['lan'], None)

                # 給予定位
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url=relocation,
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                message1 = FlexSendMessage(alt_text="hello", contents=bubble1)
                line_bot_api.reply_message(
                    event.reply_token, [TextSendMessage(text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText')), message1])

            else:  # user有資料
                # 拿user經緯度
                lat = user['lat']
                lng = user['lng']
                print(lat)
                print(lng)
                # 離user最近的五筆推薦
                res = getRestuarantsByPref(user['preference'],[lng,lat])
                
                #print(res)
                #######這裡要改，沒有網址跟地址
                def getphoto(name,lat,lng):###拿照片METHOD
                    restaurantSearch ="https://maps.googleapis.com/maps/api/place/nearbysearch/json?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&location={},{}&rankby=distance&type=restaurant&language=zh-TW".format(lat,lng)
                    restaurantReq = requests.get(restaurantSearch)
                    restaurant_dict = restaurantReq.json()
                    newname=name.split(' - ')
                    
                    photoReference=''
                    photoWidth=''
                    address='無地址'
                    for i in range(len(restaurant_dict)):
                        if newname[0] in str(restaurant_dict['results'][i]['name']) :
                            try:
                                photoReference= restaurant_dict['results'][i]['photos'][0]['photo_reference']
                            except:
                                photoReference=''
                            try:
                                photoWidth=restaurant_dict['results'][i]['photos'][0]['width']
                            except:
                                photoWidth=''
                            try:  
                                address=restaurant_dict['results'][i]['vicinity']
                            except:
                                address='無地址'
                    if photoReference=='':
                        thumbnailImageUrl ="https://imgur.com/XWtpbnt.jpg"
                    else:
                        thumbnailImageUrl = "https://maps.googleapis.com/maps/api/place/photo?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&photoreference={}&maxwidth={}".format(photoReference,photoWidth)                
                    return thumbnailImageUrl,address,newname[0]

                bubble_list = list(map(lambda i: RestuarantBubble(
                    name=trans_txt((getphoto(i['title'],i['location']['lat'],i['location']['lng'])[2]),user['lan']).get('TranslatedText'), 
                    address=trans_txt((getphoto(i['title'],i['location']['lat'],i['location']['lng'])[1]),user['lan']).get('TranslatedText'), 
                    time="10:00 - 23:00", 
                    ##image="https://i.imgur.com/TwKsV8T.jpg",
                    image=getphoto(i['title'],i['location']['lat'],i['location']['lng'])[0],  
                    website="https://example.com",
                    lat=i['location']['lat'],
                    lng=i['location']['lng'], 
                    lan = user['lan'],
                    rating=i['rating']), res))
                
            

                #print(bubble_list)
                carousel = CarouselContainer(contents=bubble_list)

                #######這裡要改
                newBubble = BubbleContainer(
                    body=BoxComponent(
                        layout='vertical',
                        contents=[
                            TextComponent(text=trans_txt('需要更詳細的推薦嗎?',user['lan']).get('TranslatedText')),
                            ButtonComponent(action=URIAction(uri='line://nv/location',text=trans_txt('重新定位',user['lan']).get('TranslatedText'), label=trans_txt('重新定位',user['lan']).get('TranslatedText'))),
                            ButtonComponent(action=URIAction(uri='https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id=1606988072&redirect_uri=https://lineloginscu.herokuapp.com/&state=abcde&scope=openid%20profile',text=trans_txt('重新設定喜好',user['lan']).get('TranslatedText'), label=trans_txt('重新設定喜好',user['lan']).get('TranslatedText')))
                        ]
                    )
                )

                # 轉成使用者輸入的語言回覆

                line_bot_api.reply_message(event.reply_token, [
                    TextSendMessage(text=trans_txt('讓我來推薦你附近餐廳～',user['lan']).get('TranslatedText')),
                    FlexSendMessage(alt_text=trans_txt("推薦餐廳",user['lan']).get('TranslatedText'), contents=carousel),
                    FlexSendMessage(alt_text=trans_txt("額外設定",user['lan']).get('TranslatedText'), contents=newBubble)
                ])

        elif text == '住宿' or event.message.text == '宿泊施設':
            print(event.message.text)
            def getphoto(name,lat,lng):###拿照片METHOD
                    restaurantSearch ="https://maps.googleapis.com/maps/api/place/nearbysearch/json?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&location={},{}&rankby=distance&language=zh-TW".format(lat,lng)
                    restaurantReq = requests.get(restaurantSearch)
                    restaurant_dict = restaurantReq.json()
                    newname=name.split(' - ')
                    
                    photoReference=''
                    photoWidth=''
                    address='無地址'
                    for i in range(len(restaurant_dict)):
                        if newname[0] in str(restaurant_dict['results'][i]['name']) or newname[0] == str(restaurant_dict['results'][i]['name']) or str(restaurant_dict['results'][i]['name'])  in newname[0]  :
                            try:
                                photoReference= restaurant_dict['results'][i]['photos'][0]['photo_reference']
                            except:
                                photoReference=''
                            try:
                                photoWidth=restaurant_dict['results'][i]['photos'][0]['width']
                            except:
                                photoWidth=''
                            try:  
                                address=restaurant_dict['results'][i]['vicinity']
                            except:
                                address='無地址'
                    if photoReference=='':
                        thumbnailImageUrl ="https://imgur.com/I9zmjwp.jpg"
                    else:
                        thumbnailImageUrl = "https://maps.googleapis.com/maps/api/place/photo?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&photoreference={}&maxwidth={}".format(photoReference,photoWidth)                
                    return thumbnailImageUrl,address,newname[0]
            # user沒資料
            if(user == None or user['lat'] == None):
                language = "zh-TW"
                if user:
                    language = user['lan']

                relocation = {
                    'zh-TW' : 'https://i.imgur.com/Mu3OmsY.jpg',
                    'en' : 'https://imgur.com/QPeSsju.jpg',
                    'ja' : 'https://imgur.com/MjuLXTe.jpg',
                    'ko' : 'https://imgur.com/2uu74Xs.jpg'
                }.get(user['lan'], None)

                # 給予定位
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url=relocation,
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                message1 = FlexSendMessage(alt_text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText'), contents=bubble1)
                line_bot_api.reply_message(
                    event.reply_token, [TextSendMessage(text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText')), message1])

            else:  # user有資料
                # 拿user經緯度
                lat = user['lat']
                lng = user['lng']
                print(lat)
                print(lng)
                # 離user最近的五筆推薦
                lodging = client.data.lodging_tag
                lodging.ensure_index([('location', '2d')])
                res = lodging.find({"location": {"$near": [lat, lng]}}).limit(5)

                # build bubble list
                bubble_list = list(map(lambda i: LodgingBubble(
                    name=trans_txt((getphoto(i['title'],i['location']['lat'],i['location']['lng'])[2]),user['lan']).get('TranslatedText'), 
                    address=trans_txt((getphoto(i['title'],i['location']['lat'],i['location']['lng'])[1]),user['lan']).get('TranslatedText'), 
                    lat=i['location']['lat'],
                    lng=i['location']['lng'],
                    lan=user['lan'],
                    picture=getphoto(i['title'],i['location']['lat'],i['location']['lng'])[0], 
                ), res))
                
                
                
                carousel = CarouselContainer(contents=bubble_list)

                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=trans_txt("讓我來推薦你附近住宿～",user['lan']).get('TranslatedText')),
                                                            FlexSendMessage(alt_text=trans_txt("讓我來推薦你附近住宿～",user['lan']).get('TranslatedText'), contents=carousel)])

        elif text == '活動' or event.message.text == '활동에 참여할 수 있습니다' :
            print(event.message.text)
            # user沒資料
            if user == None or user['lat'] == None:
                language = "zh-TW"
                if user:
                    language = user['lan']

                relocation = {
                    'zh-TW' : 'https://i.imgur.com/Mu3OmsY.jpg',
                    'en' : 'https://imgur.com/QPeSsju.jpg',
                    'ja' : 'https://imgur.com/MjuLXTe.jpg',
                    'ko' : 'https://imgur.com/2uu74Xs.jpg'
                }.get(user['lan'], None)
                # 給予定位
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url='https://i.imgur.com/Mu3OmsY.jpg',
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                message1 = FlexSendMessage(alt_text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText'), contents=bubble1)
                line_bot_api.reply_message(
                    event.reply_token, [TextSendMessage(text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText')), message1])

            else:  # user有資料
                # 拿user經緯度
                lat = user['lat']
                lng = user['lng']
                print(lat)
                print(lng)
                # 離user最近的五筆推薦
                activity = client.data.activity_data
                activity.ensure_index([('location', '2d')])
                res = activity.find({"location": {"$near": [lat, lng]}}).limit(5)

                # build bubble list
                bubble_list = list(map(lambda i: ActivityBubble(
                    name=trans_txt(i['name'],user['lan']).get('TranslatedText'), 
                    address=trans_txt((i['Add']or "無地址"),user['lan']).get('TranslatedText'), 
                    lat=i['location']['lat'],
                    lng=i['location']['lng'], 
                    lan=user['lan'],
                    picture=checkUrl(i['Picture']), 
                    website=i['Website']or "https://www.google.com/search?q={searchname}".format(searchname=i['name'])
                    ), res))
                
                carousel = CarouselContainer(contents=bubble_list)

                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=trans_txt("讓我來推薦你附近活動～",user['lan']).get('TranslatedText')),
                                                            FlexSendMessage(alt_text=trans_txt("讓我來推薦你附近活動～",user['lan']).get('TranslatedText'), contents=carousel)])

        elif text == '景點' or event.message.text == '観光名所':
            print(event.message.text)
            # user沒資料
            if user == None or user['lat'] == None:
                language = "zh-TW"
                if user:
                    language = user['lan']

                relocation = {
                    'zh-TW' : 'https://i.imgur.com/Mu3OmsY.jpg',
                    'en' : 'https://imgur.com/QPeSsju.jpg',
                    'ja' : 'https://imgur.com/MjuLXTe.jpg',
                    'ko' : 'https://imgur.com/2uu74Xs.jpg'
                }.get(user['lan'], None)
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url='https://i.imgur.com/Mu3OmsY.jpg',
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                message1 = FlexSendMessage(alt_text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText'), contents=bubble1)
                line_bot_api.reply_message(
                    event.reply_token, [TextSendMessage(text=trans_txt("資料庫沒有你的位置資料，請重新定位位置喔!",language).get('TranslatedText')), message1])
            else:
                lat = user['lat']
                lng = user['lng']
                print(lat)
                print(lng)

                scenic_spot = client.data.scenic_spot
                scenic_spot.ensure_index([('location', '2d')])
                res = scenic_spot.find(
                    {"location": {"$near": [lng, lat]}}).limit(5)
                
                def getphoto(name,lat,lng,add):
                    restaurantSearch ="https://maps.googleapis.com/maps/api/place/nearbysearch/json?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&location={},{}&rankby=distance&locationbias=circle:20000&language=zh-TW".format(lat,lng)
                    restaurantReq = requests.get(restaurantSearch)
                    restaurant_dict = restaurantReq.json()
                
                
                    photoReference=''
                    photoWidth=''
                    for i in range(len(restaurant_dict)):
                        if str(restaurant_dict['results'][i]['name']) in name or name in str(restaurant_dict['results'][i]['name']) :
                            try: 
                                photoReference= restaurant_dict['results'][i]['photos'][0]['photo_reference']
                                photoWidth=restaurant_dict['results'][i]['photos'][0]['width']
                            except:
                                photoReference=''

                        elif add in str(restaurant_dict['results'][i]['vicinity']) or str(restaurant_dict['results'][i]['vicinity']) in add:
                            try: 
                                photoReference= restaurant_dict['results'][i]['photos'][0]['photo_reference']
                                photoWidth=restaurant_dict['results'][i]['photos'][0]['width']
                            except:
                                photoReference=''  
                            break
                            
                    if photoReference=='':
                        thumbnailImageUrl ="https://imgur.com/PzggTWr.jpg"
                    else:
                        thumbnailImageUrl = "https://maps.googleapis.com/maps/api/place/photo?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&photoreference={}&maxwidth={}".format(photoReference,photoWidth)                
                    return thumbnailImageUrl
                
                
                bubble_list = list(map(lambda i: ScenicSpotBubble(
                    name=trans_txt(i['name'],user['lan']).get('TranslatedText'),
                    address=trans_txt(i['Add'],user['lan']).get('TranslatedText'),
                    description=trans_txt((i['Description']or "無敘述"),user['lan']).get('TranslatedText') ,
                    lat=i['location']['lat'],
                    lng=i['location']['lng'],
                    lan=user['lan'],
                    mapurl='https://www.google.com/maps/search/?api=1&query=TASTY西堤牛排中和板南店',
                    image=getphoto(i['name'],i['location']['lat'],i['location']['lng'],i['Add']),
                ), res))

                carousel = CarouselContainer(contents=bubble_list)
                #print(carousel)
                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=trans_txt("讓我來推薦你附近景點～",user['lan']).get('TranslatedText')),
                                                            FlexSendMessage(alt_text=trans_txt("讓我來推薦你附近景點～",user['lan']).get('TranslatedText'), contents=carousel)])

        elif text == '登入':
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={os.environ.get('LOGIN_ID')}&redirect_uri={os.environ.get('LOGIN_REDIRECT')}&state=abcde&scope=openid%20profile"))

        elif text == "定位":
            message = TemplateSendMessage(
                alt_text='Confirm template',
                template=ConfirmTemplate(
                    text=trans_txt('是否要修改定位?',user['lan']).get('TranslatedText'),
                    actions=[
                        PostbackTemplateAction(
                            label='postback',
                            text='postback text',
                            data='action=buy&itemid=1'
                        ),
                        URITemplateAction(
                            label='location',
                            uri='line://nv/location'
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, message)

        elif text == "選單" or text == "功能表" or text == "從選單中選取" or text == "選擇菜單":
            # user沒資料
            if user == None:
                bubble = BubbleContainer(
                    direction='ltr',
                    body=BoxComponent(
                        layout='vertical',
                        contents=[
                            # title
                            TextComponent(text='功能推薦 / Recommendations', weight='bold', size='lg'),
                        ],
                    ),
                    footer=BoxComponent(
                        layout='vertical',
                        spacing='xs',
                        contents=[
                        # first row
                        BoxComponent(
                            layout='horizontal',
                            spacing='xs',
                            contents=[
                                # callAction, separator, websiteAction
                                SpacerComponent(size='sm'),
                                # callAction
                                ImageComponent(
                                    url='https://i.imgur.com/3lDSAzf.jpg',
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label='餐廳', text='餐廳')
                                ),

                                # separator
                                SeparatorComponent(),
                                # websiteAction
                                ImageComponent(
                                    url='https://i.imgur.com/Du2ZFZW.jpg',
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label='住宿', text='住宿')
                                )
                            ]
                        ),
                        # second row
                        BoxComponent(
                            layout='horizontal',
                            spacing='xs',
                            contents=[
                                # callAction, separator, websiteAction
                                SpacerComponent(size='sm'),
                                # callAction
                                ImageComponent(
                                    url='https://i.imgur.com/3QOwxjC.jpg',
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label='景點', text='景點')
                                ),
                                # separator
                                SeparatorComponent(),
                                # websiteAction
                                ImageComponent(
                                    url='https://i.imgur.com/N0u3MbN.jpg',
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label='活動', text='活動')
                                )
                            ]
                        ),
                        ]
                    ),
                )
                message = FlexSendMessage(alt_text="hello", contents=bubble)

                #重新定位
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url='https://i.imgur.com/Mu3OmsY.jpg',
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                message1 = FlexSendMessage(alt_text="hello", contents=bubble1)
                line_bot_api.reply_message(event.reply_token, [message, message1])
            else:
                fuctiontxt = { 
                    'zh-TW' : '功能推薦 / Recommendations',
                    'en' : 'Recommendations',
                    'ja' : '機能に関する推奨事項',
                    'ko' : '기능 권장 사항'
                }.get(user['lan'], None)

                #圖片更改
                pic_res = {
                    'zh-TW' : 'https://i.imgur.com/3lDSAzf.jpg',
                    'en' : 'https://imgur.com/XWtpbnt.jpg',
                    'ja' : 'https://imgur.com/MBLOIcK.jpg',
                    'ko' : 'https://imgur.com/504X61v.jpg'
                }.get(user['lan'], None)
                pic_hotel = {
                    'zh-TW' : 'https://i.imgur.com/Du2ZFZW.jpg',
                    'en' : 'https://imgur.com/I9zmjwp.jpg',
                    'ja' : 'https://imgur.com/xdTwSAc.jpg',
                    'ko' : 'https://imgur.com/dgRSNO8.jpg'
                }.get(user['lan'], None)
                pic_act = {
                    'zh-TW' : 'https://i.imgur.com/N0u3MbN.jpg',
                    'en' : 'https://imgur.com/FfiIWot.jpg',
                    'ja' : 'https://imgur.com/JErghGx.jpg',
                    'ko' : 'https://imgur.com/ZXHNLFp.jpg'
                }.get(user['lan'], None)
                pic_spot = {
                    'zh-TW' : 'https://i.imgur.com/3QOwxjC.jpg',
                    'en' : 'https://imgur.com/PzggTWr.jpg',
                    'ja' : 'https://imgur.com/5y1Ba1P.jpg',
                    'ko' : 'https://imgur.com/uoDvVLR.jpg'
                }.get(user['lan'], None)
                #功能推薦
                bubble = BubbleContainer(
                    direction='ltr',
                    body=BoxComponent(
                        layout='vertical',
                        contents=[
                        # title
                            TextComponent(text=fuctiontxt, weight='bold', size='lg'),
                        ],
                    ),
                    footer=BoxComponent(
                        layout='vertical',
                        spacing='xs',
                        contents=[
                        # first row

                        BoxComponent(
                            layout='horizontal',
                            spacing='xs',
                            contents=[
                                # callAction, separator, websiteAction
                                SpacerComponent(size='sm'),
                                # callAction
                                ImageComponent(
                                    url=pic_res,
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label=trans_txt('餐廳',user['lan']).get('TranslatedText'), text=trans_txt('餐廳',user['lan']).get('TranslatedText'))
                                ),

                                # separator
                                SeparatorComponent(),
                                # websiteAction
                                ImageComponent(
                                    url=pic_hotel,
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label=trans_txt('住宿',user['lan']).get('TranslatedText'), text=trans_txt('住宿',user['lan']).get('TranslatedText'))
                                )
                            ]
                        ),
                        # second row
                        BoxComponent(
                            layout='horizontal',
                            spacing='xs',
                            contents=[
                                # callAction, separator, websiteAction
                                SpacerComponent(size='sm'),
                                # callAction
                                ImageComponent(
                                    url=pic_spot,
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label=trans_txt('景點',user['lan']).get('TranslatedText'), text=trans_txt('景點',user['lan']).get('TranslatedText'))
                                ),
                                # separator
                                SeparatorComponent(),
                                # websiteAction
                                ImageComponent(
                                    url=pic_act,
                                    size='full',
                                    aspect_ratio='20:13',
                                    aspect_mode='cover',
                                    action=MessageAction(label=trans_txt('活動',user['lan']).get('TranslatedText'), text=trans_txt('活動',user['lan']).get('TranslatedText'))
                                )
                            ]
                        ),
                        ]
                    ),
                )
                message = FlexSendMessage(alt_text="hello", contents=bubble)

                relocation = {
                    'zh-TW' : 'https://i.imgur.com/Mu3OmsY.jpg',
                    'en' : 'https://imgur.com/QPeSsju.jpg',
                    'ja' : 'https://imgur.com/MjuLXTe.jpg',
                    'ko' : 'https://imgur.com/2uu74Xs.jpg'
                }.get(user['lan'], None)
                #重新定位
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url=relocation,
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                message1 = FlexSendMessage(alt_text="hello", contents=bubble1)
                line_bot_api.reply_message(event.reply_token, [message, message1])

        elif text == "語言":
            newbubble = BubbleContainer(
                body=BoxComponent(layout='vertical', contents=[
                    TextComponent(text='語言 / Language / 言語 / 언어 / язык'),
                    ButtonComponent(action=MessageAction(
                        label='中文', text='中文')),
                    ButtonComponent(action=MessageAction(
                        label='English', text='English')),
                    ButtonComponent(action=MessageAction(
                        label='日本語', text='日本語')),
                    ButtonComponent(action=MessageAction(
                        label='한국어', text='한국어')),
                ]))

            line_bot_api.reply_message(event.reply_token, FlexSendMessage(
                alt_text="語言設定", contents=newbubble))

        elif text == "中文" or text == "英語" or text == "日本語" or text == "韓國人":
            lan = { 
            '中文' : 'zh-TW',
            '英語' : 'en',
            '日本語' : 'ja',
            '韓國人' : 'ko',
            }.get(text, None)

            if (user != None):  # user有資料，更新
                print("NOT EMPTY")
                print("language = "+lan)
                user['lan'] = lan
                # print("user_lan="+str(user['lan']))
                collection.update_one(condition, {'$set': user})
            else:  # user沒有資料，新增
                print("EMPTY")
                userdict = {"userId": userId, "lat": None, "lng": None, "lan": lan, "preference": {"like": [], "ok": [], "dislike": []}}
                collection.insert_one(userdict)

            bubble1 = BubbleContainer(
                direction='ltr',
                hero=ImageComponent(
                    url='https://imgur.com/6u5XWJX.jpg',
                    size='full',
                    aspect_ratio='5:1',
                    aspect_mode='fit',
                    action=MessageAction(label=trans_txt('選單',lan).get('TranslatedText'), text=trans_txt('選單',lan).get('TranslatedText'))
                ),
            )
            print("選單："+trans_txt('選單',lan).get('TranslatedText'))
            # 轉成使用者輸入的語言回覆
            trans_text = translate_text("已變更你的語言囉～開始使用推薦功能吧！","zh-TW",lan).get('TranslatedText')

            line_bot_api.reply_message(event.reply_token, [TextSendMessage(
                text=trans_text), FlexSendMessage(alt_text="已變更你的語言囉～開始使用推薦功能吧！", contents=bubble1)])

        elif text == "天氣":
            if (user['lat'] != None):  # user有資料，拿經緯度
                print("NOT EMPTY")
                lat = user['lat']
                lng = user['lng']
                # 去天氣API拿天氣資料 並回傳JSON 處理JSON拿天氣資料
                complete_url = 'https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid=0056a083378c9466f69a017d5c17c4f4&lang=zh_tw'.format(
                lat, lng)
                print(complete_url)
                response = requests.get(complete_url)
                #print(response)
                x = response.json()
                # 拿天氣資料
                city_name = x['name']
                icon = x['weather'][0]['icon']  # 天氣狀況
                icon_url = 'https://openweathermap.org/img/wn/{}@2x.png'.format(icon)
                print(icon_url)
                description = x['weather'][0]['description']
                temp_min = repr(x['main']['temp_min'])  # 最低溫度
                temp_min = repr(round((float(temp_min)-273.15), 2))
                temp_max = repr(x['main']['temp_max'])  # 最最高溫度
                temp_max = repr(round((float(temp_max)-273.15), 2))
                print(description)
                # 以上皆對

                # 天氣資訊欄
                bubble_1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url=icon_url,  # 貌似出錯 解法: 一定要+S在HTTP後面
                        size='lg',
                        aspect_ratio='20:13',
                        aspect_mode='cover'
                    ),
                    body=BoxComponent(
                        layout='vertical',
                        contents=[
                            # title
                            TextComponent(text=city_name, weight='bold', size='xl'),
                            # review
                            # info
                            BoxComponent(
                                layout='vertical',
                                margin='lg',
                                spacing='sm',
                                contents=[
                                    BoxComponent(
                                        layout='baseline',
                                        spacing='sm',
                                        contents=[
                                            TextComponent(
                                                text=trans_txt('天氣狀況',user['lan']).get('TranslatedText'),
                                                color='#aaaaaa',
                                                size='sm',
                                                flex=5
                                            ),
                                            TextComponent(
                                                text=trans_txt(description,user['lan']).get('TranslatedText'),
                                                wrap=True,
                                                color='#666666',
                                                size='sm',
                                                flex=5
                                            )
                                        ],
                                    ),
                                    BoxComponent(
                                        layout='baseline',
                                        spacing='sm',
                                        contents=[
                                            TextComponent(
                                                text=trans_txt('最高溫度',user['lan']).get('TranslatedText'),
                                                color='#aaaaaa',
                                                size='sm',
                                                flex=7
                                            ),
                                            TextComponent(
                                                text=temp_max,
                                                wrap=True,
                                                color='#666666',
                                                size='sm',
                                                flex=5,
                                            ),
                                        ],
                                    ),
                                    BoxComponent(
                                        layout='baseline',
                                        spacing='sm',
                                        contents=[
                                            TextComponent(
                                                text=trans_txt('最低溫度',user['lan']).get('TranslatedText'),
                                                color='#aaaaaa',
                                                size='sm',
                                                flex=7
                                            ),
                                            TextComponent(
                                                text=temp_min,
                                                wrap=True,
                                                color='#666666',
                                                size='sm',
                                                flex=5,
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                    footer=BoxComponent(
                        layout='vertical',
                        spacing='sm',
                        contents=[
                            TextComponent(
                                text=' ',
                                color='#aaaaaa',
                                size='sm',
                                flex=1
                            )
                        ]
                    )
                )
                message1 = FlexSendMessage(alt_text="天氣狀況", contents=bubble_1)
                
                relocation = {
                    'zh-TW' : 'https://i.imgur.com/Mu3OmsY.jpg',
                    'en' : 'https://imgur.com/QPeSsju.jpg',
                    'ja' : 'https://imgur.com/MjuLXTe.jpg',
                    'ko' : 'https://imgur.com/2uu74Xs.jpg'
                }.get(user['lan'], None)
                bubble_2 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url=relocation,
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    )
                )
                message2 = FlexSendMessage(alt_text="定位", contents=bubble_2)
                line_bot_api.reply_message(event.reply_token, [message1, message2])
            

            else:  # user沒有資料，要定位
                print("EMPTY")
                bubble1 = BubbleContainer(
                    direction='ltr',
                    hero=ImageComponent(
                        url='https://i.imgur.com/Mu3OmsY.jpg',
                        size='full',
                        aspect_ratio='5:1',
                        aspect_mode='fit',
                        action=URIAction(uri='line://nv/location', label='label')
                    ),
                )
                line_bot_api.reply_message(
                    event.reply_token,
                    FlexSendMessage(alt_text="定位", contents=bubble1))
            
        else:
            ai = apiai.ApiAI(os.environ.get('CLIENT_ACCESS_TOKEN'))
            request = ai.text_request()

            request.lang = 'tw'  # optional, default value equal 'en'

            request.query = event.message.text
            response = request.getresponse().read().decode()
            result = json.loads(response)
            # 轉成使用者輸入的語言回覆
            trans_text = translate_text(result['result']['fulfillment']['speech'],"zh-TW",language).get('TranslatedText')

            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=trans_text))


    def checkUrl(url):
        return url if url.startswith("https") else 'https://i.imgur.com/lQVr6vU.jpg'

    @handler.add(MessageEvent, message=LocationMessage)
    def handle_location(event):
        # user經緯度及ID
        lat = event.message.latitude
        lng = event.message.longitude
        userId = event.source.user_id
        print("///", lat, " ", lng, "/////////", userId)
        # DB裡面找user是否存在
        client = pymongo.MongoClient(
            "mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/test?retryWrites=true&w=majority")
        db = client.data
        collection = db.user
        condition = {'userId': userId}
        user = collection.find_one(condition)

        if (user != None):  # user有資料，更新
            print("NOT EMPTY")
            user['lat'] = lat
            user['lng'] = lng
            collection.update_one(condition, {'$set': user})
        else:  # user沒有資料，新增
            print("EMPTY")
            user = {"userId": userId, "lat": lat, "lng": lng,"lan" : "zh-TW",
                        "preference": {"like": [], "ok": [], "dislike": []}}
            collection.insert_one(user)

        # 去天氣API拿天氣資料 並回傳JSON 處理JSON拿天氣資料
        complete_url = 'https://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid=0056a083378c9466f69a017d5c17c4f4&lang=zh_tw'.format(lat, lng)
        print(complete_url)
        response = requests.get(complete_url)
        print(response)
        x = response.json()
        # 拿天氣資料
        city_name = x['name']
        icon = x['weather'][0]['icon']  # 天氣狀況
        icon_url = 'https://openweathermap.org/img/wn/{}@2x.png'.format(icon)
        print(icon_url)
        description = x['weather'][0]['description']
        temp_min = repr(x['main']['temp_min'])  # 最低溫度
        temp_min = repr(round((float(temp_min)-273.15), 2))
        temp_max = repr(x['main']['temp_max'])  # 最最高溫度
        temp_max = repr(round((float(temp_max)-273.15), 2))
        print(description)
        # 以上皆對

        #推薦選單
        bubbl_1 = BubbleContainer(
                direction='ltr',
                hero=ImageComponent(
                    url='https://imgur.com/6u5XWJX.jpg',
                    size='full',
                    aspect_ratio='5:1',
                    aspect_mode='fit',
                    action=MessageAction(label=trans_txt('選單',user['lan']).get('TranslatedText'), text=trans_txt('選單',user['lan']).get('TranslatedText'))
                ),
            )
    
        # 天氣資訊欄
        bubble_2 = BubbleContainer(
            direction='ltr',
            hero=ImageComponent(
                url=icon_url,  # 貌似出錯 解法: 一定要+S在HTTP後面
                size='lg',
                aspect_ratio='20:13',
                aspect_mode='cover'
            ),
            body=BoxComponent(
                layout='vertical',
                contents=[
                    # title
                    TextComponent(text=city_name, weight='bold', size='xl'),
                    # review
                    # info
                    BoxComponent(
                        layout='vertical',
                        margin='lg',
                        spacing='sm',
                        contents=[
                            BoxComponent(
                                layout='baseline',
                                spacing='sm',
                                contents=[
                                    TextComponent(
                                        text=trans_txt('天氣狀況',user['lan']).get('TranslatedText'),
                                        color='#aaaaaa',
                                        size='sm',
                                        flex=5
                                    ),
                                    TextComponent(
                                        text=trans_txt(description,user['lan']).get('TranslatedText'),
                                        wrap=True,
                                        color='#666666',
                                        size='sm',
                                        flex=5
                                    )
                                ],
                            ),
                            BoxComponent(
                                layout='baseline',
                                spacing='sm',
                                contents=[
                                    TextComponent(
                                        text=trans_txt('最高溫度',user['lan']).get('TranslatedText'),
                                        color='#aaaaaa',
                                        size='sm',
                                        flex=7
                                    ),
                                    TextComponent(
                                        text=temp_max,
                                        wrap=True,
                                        color='#666666',
                                        size='sm',
                                        flex=5,
                                    ),
                                ],
                            ),
                            BoxComponent(
                                layout='baseline',
                                spacing='sm',
                                contents=[
                                    TextComponent(
                                        text=trans_txt('最低溫度',user['lan']).get('TranslatedText'),
                                        color='#aaaaaa',
                                        size='sm',
                                        flex=7
                                    ),
                                    TextComponent(
                                        text=temp_min,
                                        wrap=True,
                                        color='#666666',
                                        size='sm',
                                        flex=5,
                                    ),
                                ],
                            ),
                        ],
                    )
                ],
            ),
            footer=BoxComponent(
                layout='vertical',
                spacing='sm',
                contents=[
                    TextComponent(
                        text=' ',
                        color='#aaaaaa',
                        size='sm',
                        flex=1
                    )
                ]
            )
        )

        line_bot_api.reply_message(
            event.reply_token,
            [TextMessage(text=trans_txt("接收到位置囉~",user['lan']).get('TranslatedText')),
            FlexSendMessage(alt_text="推薦選單", contents=bubbl_1)]
        )

    def translate_text(text,SRC_LANG,TRG_LANG):
        translate = boto3.client(service_name='translate',region_name='us-east-1', use_ssl=True)  # aws翻譯
        response = translate.translate_text(
            Text=text,
            SourceLanguageCode=SRC_LANG,
            TargetLanguageCode=TRG_LANG
        )

        return response

    def trans_txt(text,TRG_LANG):
        translate = boto3.client(service_name='translate',region_name='us-east-1', use_ssl=True)  # aws翻譯
        response = translate.translate_text(
            Text=text,
            SourceLanguageCode="zh-TW",
            TargetLanguageCode=TRG_LANG
        )

        return response

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return {'statusCode': 400, 'body': 'InvalidSignatureError'}
    return {'statusCode': 200, 'body': 'OK'}
