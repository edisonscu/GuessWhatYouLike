from linebot.models import *
import boto3

class LodgingBubble(BubbleContainer):
    def __init__(self,name,address,lat,lng,lan,picture):
        def trans_txt(text,TRG_LANG):
            translate = boto3.client(service_name='translate',region_name='us-east-1', use_ssl=True)  # aws翻譯
            response = translate.translate_text(
                Text=text,
                SourceLanguageCode="zh-TW",
                TargetLanguageCode=TRG_LANG
            )

            return response

        super().__init__(direction='ltr',
            hero=ImageComponent(
                url=picture,  ##########貌似出錯 解法: 一定要+S在HTTP後面
                size='full',
                aspect_ratio='20:13',
                aspect_mode='cover'
            ),
            body=BoxComponent(
                layout='vertical',
                contents=[
                    # title
                    TextComponent(text=name, weight='bold', size='lg'),
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
                                        text='Address',
                                        color='#aaaaaa',
                                        size='sm',
                                        flex=3
                                    ),
                                    TextComponent(
                                        text=address,
                                        wrap=True,
                                        color='#666666',
                                        size='sm',
                                        flex=5,
                                    )
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
                       
                    
                    ButtonComponent(
                        style='link',
                        height='sm',
                        action=PostbackAction(
                            label=trans_txt('查看位置',lan).get('TranslatedText'),
                            display_text=trans_txt('查看位置',lan).get('TranslatedText'),
                            data=f'title={name}&address={address}&lat={lat}&lng={lng}'
                            )
                     )
                        
                    ]
            ))
 