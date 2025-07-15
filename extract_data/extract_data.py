import requests
import os
from lxml import etree
import json
import time 
class Author:
    def __init__(self, name: str = '', 
                 doi: str = '', 
                 email: str = '',
                 institution = [],
                 departament = [],
                 country = [],
                 settlement = []
                ):
        self.name = name
        self.doi = doi
        self.email = email
        self.institution = institution
        self.settlement = settlement
        self.department = departament
        self.country =  country
    
    def to_dict(self):
        return {
            'name': self.name,
            'doi': self.doi,
            'email': self.email,
            'department': self.department,
            'institution':self.institution,
            'country':self.country,
            'settlement':self.settlement
        }
    
    def __str__(self):
        return f"Actor(name='{self.name}', doi='{self.doi}', email='{self.email}', country='{",".join(self.country)}', department='{','.join(self.department)}', institution='{self.institution}', settlement='{','.join(self.settlement)}')"

class PDF:
    def __init__(self):
        self.authors = []
        self.title=''
        self.keywords = []
        self.references = []

    def to_dict(self):
         return {
              'authors':[x.to_dict() if isinstance(x,Author) else x for x in self.authors],
              'title':self.title,
              'keywords':self.keywords,
              'references':self.references
         }  
    def __str__(self):
         return f"PDF(title='{self.title if self.title else "unknown"}', authors='{[x.to_dict() if isinstance(x,Author) else x for x in self.authors]}', keywords='{self.keywords}', references='{self.references}')"


class PDFExtractor:

    def __init__(self,path:str,
                 url:str = "http://localhost:8070/api/processHeaderDocument",
                 ns:dict={'tei':'http://www.tei-c.org/ns/1.0'},
                 headers:dict={'Accept':'application/xml'},
                 only_extract_ref:bool = False,
                 name_file:str = 'extract_result.json'
                ):
        self.path = path
        self.url = url
        self.ns = ns
        self.headers = headers
        self.root = None
        self.ef = only_extract_ref
        self.name_file=name_file

    def _references(self,f):
        url= 'http://localhost:8070/api/processReferences'
        file = self.open_pdf(f)
        response = requests.post(url, files={'input': file}, headers=self.headers)
        xml_content = response.text
        #ns={'xmlns':'http:///www.tei-c.org/ns/1.0',"xlink":'http://www.w3.org/1999/xlink',"mml":'http://www.w3.org/1998/Math/MathML'}
        root = etree.fromstring(xml_content.encode('utf-8'))
        a = root.xpath('//tei:listBibl/tei:biblStruct',namespaces=self.ns)
        c=[]
        for i in a:
            ti = i.xpath('.//tei:analytic/tei:title/text()',namespaces=self.ns)
            authors = i.xpath('.//tei:analytic/tei:author',namespaces=self.ns)
            ss= []
            for aut in authors:
                forenames = aut.xpath('.//tei:forename/text()',namespaces=self.ns)
                surname = aut.xpath('.//tei:surname/text()',namespaces=self.ns)
                name = " ".join(forenames+surname)
                ss.append(name)
            journal = i.xpath('.//tei:monogr/tei:title/text()',namespaces=self.ns)
            year = i.xpath('.//tei:imprint/tei:date/text()',namespaces=self.ns)
            c.append({"title":ti,'authors':ss,'journal':journal,'year':year})
        return c

    def open_pdf(self,file):
        try:
            return open(os.path.join(self.path,file),'rb')
        except:
            raise FileNotFoundError("revisa que las rutas sean correctas")
        
    def _request(self,file_):
        file = self.open_pdf(file_)
        response = requests.post(self.url, files={'input': file}, headers=self.headers)
        xml_content = response.text
        self.root = etree.fromstring(xml_content.encode('utf-8'))
    

    def _parse(self,xpath):
        return self.root.xpath(xpath,namespaces=self.ns)
    
    def parse_authors(self,pdf,xpath='//tei:author'):
        title = self._parse('//tei:titleStmt/tei:title/text()')
        print("title")
        pdf.title = title 
        
        authors = self.root.xpath(xpath,namespaces=self.ns)
        for author in authors:
                
                forenames = author.xpath('.//tei:forename/text()',namespaces=self.ns)
                surname = author.xpath('.//tei:surname/text()',namespaces=self.ns)
                name = " ".join(forenames+surname)
                email =author.xpath('.//tei:email/text()',namespaces=self.ns)
                     
                af = author.xpath('.//tei:affiliation',namespaces=self.ns)
                institution = []
                department = []
                countrys = []
                settlements=[]
                for i in af:
                        dpt = i.xpath('.//tei:orgName[@type="department"]/text()',namespaces=self.ns)
                        if dpt:
                            department.append(" ".join(dpt))
                        inst = i.xpath('.//tei:orgName[@type="institution"]/text()',namespaces=self.ns)
                        if inst:
                            institution.append(" ".join(inst))
                            
                        settlement = i.xpath('.//tei:address/tei:settlement/text()',namespaces=self.ns)
                        country = i.xpath('.//tei:address/tei:country/text()',namespaces=self.ns)
                        
                        settlements.append(" ".join(settlement))
                        countrys.append(" ".join(country))
                AUTHOR = Author(name=name,email=email,country=countrys,settlement=settlements,departament=department,institution=institution)
                pdf.authors.append(AUTHOR)
        keywords = self.root.xpath('//tei:keywords/tei:term/text()',namespaces=self.ns)
        pdf.keywords = keywords
        
    def run(self):
        pdfs = {}
        l = list(os.listdir(self.path))
        total = len(l)

        for j, i in enumerate(l):
            print(f'pdf_{j+1}/{total}')
            pdf = PDF()
            if not i.endswith('.pdf'):
                 continue
            if self.ef:
                print('references')
                time.sleep(2)
                ref = self._references(i)
                pdf.references = ref
            else:
                self._request(i)
                self.parse_authors(pdf)
            pdfs[f'pdf_{j+1}'] = pdf.to_dict()

        
        with open(f"./data/{self.name_file}",'w') as f:
             json.dump(pdfs,f)
        print("done")
extractor = PDFExtractor('pdfs_papers',only_extract_ref=True,name_file='extract_ref.json')
extractor.run()