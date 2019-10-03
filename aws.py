import boto3

# constant
REGION = 'us-west-2'
SRC_LANG = 'auto'
TRG_LANG = 'ko'


#def get_translate_text(text):

    #translate = boto3.client('translate', region_name=REGION)

   #response = translate.translate_text(
   #     Text=text,
   #     SourceLanguageCode=SRC_LANG,
    #    TargetLanguageCode=TRG_LANG
   # )

    #return response


def main():
    # Text to translate
    text = """活動"""

    # From Japanese to English
    # while len(text.encode('utf-8')) > 5000:
    #   text = text[:-1]

    # From English to Japanese
    # while len(text) > 5000:
    #  text = text[:-1]

   # result = get_translate_text(text)
    #print(result.get('TranslatedText'))

    language = { #會有dic str的問題
        '英文' : 'en',
        '日本語' : 'ja',
        '韓國人' : 'ko',
        '俄語' : 'ru'
    }.get("英文", None)
    print(language)

if __name__ == '__main__':
    main()