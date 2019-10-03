import requests
import json
lat=22.9964759
lng=120.2142088
restaurantSearch ="https://maps.googleapis.com/maps/api/place/nearbysearch/json?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&location={},{}&rankby=distance&type=restaurant&language=zh-TW".format(lat,lng)
restaurantReq = requests.get(restaurantSearch)
restaurant_dict = restaurantReq.json()
name='Cafe Grazie 義式屋古拉爵 台南遠百成功店'
bravo=[]
photoReference=''
photoWidth=''
for i in range(len(restaurant_dict)):
    if name in str(restaurant_dict['results'][i]['name']) :
      photoReference= restaurant_dict['results'][i]['photos'][0]['photo_reference']
      photoWidth=restaurant_dict['results'][i]['photos'][0]['width']
  
if photoReference=='':
    photoReference=123
thumbnailImageUrl = "https://maps.googleapis.com/maps/api/place/photo?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&photoreference={}&maxwidth={}".format(photoReference,photoWidth)
print(restaurant_dict['results'][i]['vicinity'])

def getphoto(name,lat,lng):
                restaurantSearch ="https://maps.googleapis.com/maps/api/place/nearbysearch/json?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&location={},{}&rankby=distance&type=restaurant&language=zh-TW".format(lat,lng)
                restaurantReq = requests.get(restaurantSearch)
                restaurant_dict = restaurantReq.json()
                newname=name.split(' - ')
                bravo=[]
                photoReference=''
                photoWidth=''
                for i in range(len(restaurant_dict)):
                    if newname[0] in str(restaurant_dict['results'][i]['name']) :
                        photoReference= restaurant_dict['results'][i]['photos'][0]['photo_reference']
                        photoWidth=restaurant_dict['results'][i]['photos'][0]['width']
                        address=restaurant_dict['results'][i]['vicinity']
                if photoReference=='':
                    thumbnailImageUrl ="https://imgur.com/XWtpbnt.jpg"
                else:
                    thumbnailImageUrl = "https://maps.googleapis.com/maps/api/place/photo?key=AIzaSyCkzX3dPU0ny5Y7iyxIvoY6uDGS77Qelj0&photoreference={}&maxwidth={}".format(photoReference,photoWidth)                
                return thumbnailImageUrl,address
print(getphoto('Cafe Grazie 義式屋古拉爵 台南遠百成功店',22.9964759,120.2142088)[1])


