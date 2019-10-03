import json
import codecs


Activity=json.load(codecs.open('activity_final.json', 'r', 'utf-8-sig'))
print(Activity)
def getActivity(Member_Px,Member_Py):
    
    answer = []
    i=0
    for index in range (len(Activity['Info'])):
     if (Activity['Info'][index]['Px']==Member_Px and
         Activity['Info'][index]['Py']==Member_Py):

         answer.append(["座標: "+Activity['Info'][index]['Name'],
                        "網頁: "+Activity['Info'][index]['Website'],
                        "敘述: "+ Activity['Info'][index]['Description'],
                        "經度: "+ str(Activity['Info'][index]['Px']),
                        "緯度: "+ str(Activity['Info'][index]['Py'] ) ])
         
         break
     
    

    return answer

print (getActivity(121.683852,25.19107))
