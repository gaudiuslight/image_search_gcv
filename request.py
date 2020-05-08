from google.cloud import vision
from google.cloud.vision import types
import base64
import io
 
class Request:

    def __init__(self, image=''):
        MAX_RESULTS = 500
        self.source = image
        self.request = {
            'image':{},
            #'image': {'source': {'image_uri' : ''}},
            'features':[
                {'type':vision.enums.Feature.Type.TEXT_DETECTION, 'max_results': MAX_RESULTS},
            ]
        }

        #request body can change depending on the image source...
        #urls are inserted directly, while local images must be loaded/encoded first
        #also the dictionary's structure is not the same for both sources
        if image.startswith('http'): 
            self.request['image']['source'] = {}
            self.request['image']['source']['image_uri'] = image
        else:
            try:
                self.request['image']['content'] = self.encode_image(image)
            except:
                raise
            
    def get_src(self):
        return self.source
    
    def get_req(self):
        return self.request

    def encode_image(self,file_name):
        print(file_name)
        with io.open(file_name, 'rb') as image_file:
            content = image_file.read()
        
        return content

