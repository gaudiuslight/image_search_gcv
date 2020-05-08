# from oauth2client.client import GoogleCredentials
from urllib.parse import urlparse
import random
import six


class Response_Handler:
    
    def __init__(self):
        self.likelihood_name = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE','LIKELY', 'VERY_LIKELY')
        self.img_info = {'source':'',
                        'web_match':{'trust': 0,
                                     'full':{'count':0,
                                             'links':[]},           #full,partial,pages -> counts and lists pages found 
                                     'partial':{'count':0,
                                                'links':[]},        #full e partial -> link di immagini trovate
                                     'pages':{'count':0,
                                              'links':[]},          #pages -> web pages in cui sono presenti immagini simili/uguali
                                     'entities':{'count':0,        #links[] da aggiungere eventualmente   
                                                 'details':[]}     #{entity:score, entity2:score,...entityn:score}
                                                                     
                                      },
                         'ocr': {},
                         'dom_clrs':{'count'  : 0,
                                     'details':[],
                                     'rgb_imp': 0,
                                     'rgb_frc': 0},     #dictionary di dictionaries, ognuna contenente i dettagli
                                                         #di uno dei colori ricavati(rgba,score,picel fraction)
                         'safe_search':{'ADULT': '',
                                        'SPOOF': '',
                                        'MEDICAL': '',
                                        'VIOLENCE': ''},
                         'labels':{'count': 0,
                                   'details':[]},         #{label1 : score, label2 : score .... labeln : score}
                         'logos':{'count':0,
                                 'details':[]},                       #{logo1 : score, logo2 : score .... logon : score}
                         'faces':{'count':0,
                                  'details':[]}
                         }
        
    def gc_web_match(self,response):
        print ('Web detection...')
        
        web = response.web_detection
        if not web:
            print('No web entities found!')
            return
        
        extract_from = {}
        for attr in dir(web):
            if attr in ['pages_with_matching_images','full_matching_images','partial_matching_images','web_entities']:
                key = str(attr).split('_')[0] if 'entities' not in attr else str(attr).split('_')[1] 
                extract_from[key] = attr
        all_links = []        
        for key , val in extract_from.items():
            infos = getattr(web,val)
            if key == 'entities':
                print ('Web entities found: {}'.format(len(infos)))
                self.img_info['web_match']['entities']['count'] = len(infos)
                for entity in infos:
                    self.img_info['web_match']['entities']['details'].append({'description':entity.description.lower(),
                                                                              'score': round(entity.score,3)})
                #self.img_info['web_match']['entities']['details'] = sorted(self.img_info['web_match']['entities']['details'],
                #                                                           key=lambda k: k['score'], reverse = True)    
            else:                
                for info in infos:
                    self.img_info['web_match'][key]['links'].append(info.url)
                    all_links.append(info.url)    
                self.img_info['web_match'][key]['count'] = len(self.img_info['web_match'][key]['links'])    
        all_links = list(set(all_links))
        self.img_info['web_match']['trust'] = self.sites_trust(all_links)
            
    def gc_OCR(self,response):
        print ('Extracring texts...')
        texts = response.text_annotations
        if not texts:
            print('No texts found!')
            return

        self.img_info['ocr']['text'] = texts[0].description

    def gc_dom_clr(self,response):
        print ('Dominant Color...')
        clr_props = response.image_properties_annotation 
        if not clr_props: 
            print('NONE!')
            return
        self.img_info['dom_clrs']['count']= len(clr_props.dominant_colors.colors)

        # to calculate the weighted average of rgb score and px_frac
        # score is assigned according to the impact/focus of a color regardless of the pixel fraction occupied 
        total_score, total_frac = 0, 0 
        rgb_imp = [0, 0, 0]   #total impacts of rgb on the pic
        rgb_frac = [0, 0, 0]   #pixel fraction occupied by rgb

        for color in clr_props.dominant_colors.colors:
            r, g, b, a = color.color.red.__int__(), color.color.green.__int__(), color.color.blue.__int__(), color.color.alpha.VALUE_FIELD_NUMBER
            score, px_frac = round(color.score,3), round(color.pixel_fraction,3)
            self.img_info['dom_clrs']['details'].append({'color':(r,g,b,a),
                                                         'score': score,
                                                         'px_frac': px_frac
                                                        })
    
            total_score += score
            total_frac += px_frac
            rgb_imp[0],rgb_imp[1],rgb_imp[2] = rgb_imp[0]+r*score, rgb_imp[1]+g*score, rgb_imp[2]+b*score
            rgb_frac[0],rgb_frac[1],rgb_frac[2] = rgb_frac[0]+r*px_frac, rgb_frac[1]+g*px_frac, rgb_frac[2]+b*px_frac
        if total_score != 0:    
            self.img_info['dom_clrs']['rgb_imp'] = [round(rgb_imp[0]/total_score,3), round(rgb_imp[1]/total_score,3), round(rgb_imp[2]/total_score,3)]  
            self.img_info['dom_clrs']['rgb_frc'] = [rgb_frac[0]/total_frac, rgb_frac[1]/total_frac, rgb_frac[2]/total_frac]
            
    def gc_safe_search(self,response):
        print ('Safe Search...')
        safe_search = response.safe_search_annotation
        if not safe_search:
            print('NONE!')
            return
        
        self.img_info['safe_search']['ADULT']    =  safe_search.adult
        self.img_info['safe_search']['SPOOF']    =  safe_search.spoof
        self.img_info['safe_search']['MEDICAL']  =  safe_search.medical
        self.img_info['safe_search']['VIOLENCE'] =  safe_search.violence
        
    
    def gc_labels(self,response):
        print ('Label...')
        labels = response.label_annotations 
        if not labels:
            print('NONE!')
            return
        self.img_info['labels']['count'] = len(labels)    
        for label in labels:      
            self.img_info['labels']['details'].append({'description':label.description.lower(),
                                                       'score' : round(label.score,3)
                                                       })

    def gc_faces(self,response):
        print ('Extracting faces...')
        faces = response.face_annotations
        if not faces:
            print('No faces found')
            return
        self.img_info['faces']['count'] = len(faces)
        avgs = {}
        strong_emotion = {}
        for face in faces:
            tmp = {}
            for f in dir(face):
                if 'likelihood' in f:
                   score = getattr(face,f) 
                   tmp[str(f)] = score
                   extracted_name = str(f).split('_likelihood')[0] 
                   # es sorrow_avg, sorrow_count instead of sorrow_likelihood_avg.. for dataset 
                   # count extreme certain sentiment (from likely to verylikely)
                   if score >= 4:
                       self.img_info['faces'][extracted_name+'_count'] = self.img_info['faces'][extracted_name+'_count'] + 1 if (extracted_name+'_count') in self.img_info['faces'] else 1
                   avgs[extracted_name + '_avg'] = avgs[extracted_name +'_avg'] + score if (extracted_name + '_avg') in avgs else score
                elif 'confidence' in f:                                 # confidence detection restituisce un percentuale
                    tmp[str(f)] = round(getattr(face,f),3)
            self.img_info['faces']['details'].append(tmp)
            
        for k, val in avgs.items():
            avgs[k] = val/len(faces)
        self.img_info['faces']['averages'] = avgs    
                    
    def gc_logos(self,response):
        print ('Extracting Logos...')
        logos = response.logo_annotations 
        if not logos:
            print('No logos found!')
            return
        self.img_info['logos']['count'] = len(logos)
        for logo in logos:
            self.img_info['logos']['details'].append({'description':logo.description,
                                                      'score':logo.score})
            
    def get_img_info(self):
        return self.img_info

