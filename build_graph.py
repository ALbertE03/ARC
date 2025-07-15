import networkx as nx
import json
import os
from collections import defaultdict
import re
from difflib import SequenceMatcher


class Graph:
    def __init__(self,path):
        self.graph = nx.Graph()
        self.path = path
        self.dict = defaultdict(set)
        self.data = self._load_data()

    def normalize_name(self, name):
        if not name:
            return ""
        normalized = re.sub(r'[^\w\s-]', '', name.lower().strip())
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    
    def same_email(self,name1,name2):
        pass

    def same_author(self,name1,name2):
        pass

    def _load_data(self):
        try:
            with open(self.path,'r') as f:
                return json.load(f)
        except:
            raise FileNotFoundError("ruta incorrecta")
            
    def save(self):
        nx.write_graphml(self.graph,'graph.graphml')

    def similarity_score(self, name1, name2):
        return SequenceMatcher(None, name1, name2).ratio()
    
    def compare_another_authors(self,name,**kwargs):
        for node in self.graph.nodes():
            type = self.graph[node]['type']
            if type=='paper' or type=='keyword':
                continue
            email1 = self.graph[node]['email']
            email2 = self
            name2 = self.graph[node]['name']
            normalized_existing_name= self.normalize_name(name2)
            normalized_add_name = self.normalize_name(name)
            self.model.predict(normalized_existing_name,normalized_add_name)


    def build(self):
        
        for _,value in self.data.items():
            title = value['title']
            keywords = value['keywords']
            authors = value['authors']
            if not self.graph.has_node(title[0]):
                self.graph.add_node(title[0],type='paper')
            for keyw in keywords:
                if not self.graph.has_node(keyw):
                    self.graph.add_node(keyw,type='keyword')
                    
                self.graph.add_edge(keyw,title[0])
                    #agrupae por temas similares
            for author in authors:
                name = author['name']
                
                normalized_name = self.normalize_name(name)
                if not self.graph.has_node(normalized_name):
                    status,prob,another = self.compare_another_authors(normalized_name,**author)
                    if not status:
                        self.graph.add_node(normalized_name,type='author',**author)
                    else:
                        normalized_name = another
                    
                if not self.graph.has_edge(normalized_name,title[0]):
                    self.graph.add_edge(normalized_name,title[0])
                

                    

                    
               
                    



g =Graph("data/extract_result.json")
g.build()